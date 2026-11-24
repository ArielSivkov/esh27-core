"""Agent brains. A brain maps an Observation (dict) to an Action (dict) under the contract.

  RuleBrain  - deterministic, free, the reference.
  TinyLMBrain - a small open model (default SmolLM2-135M-Instruct) on CPU. Costs 1 CRD per call.
               Its output must parse into a valid Action; anything else becomes 'rest'.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "contract"))
from world_contract import Action, ContractError, job_kind  # noqa: E402


def nearest_job(obs: dict) -> dict | None:
    jobs = obs.get("jobs") or []
    if not jobs:
        return None
    x, y = obs["pos"]

    def d2(j):  # jobs without a place (e.g. a street missing from the map) are desk jobs: distance 0
        if j.get("x") is None or j.get("node") is None:
            return 0.0
        return (j["x"] - x) ** 2 + (j["y"] - y) ** 2
    return min(jobs, key=d2)


def at_job(obs: dict, job: dict) -> bool:
    return job.get("node") is None or job["node"] == obs["node"]


def rule_answer(job: dict) -> dict:
    k = job_kind(job)
    if k == "photo_check":
        if job.get("d_street") is None:
            return {"verdict": "no_street"}
        return {"verdict": "consistent" if job["d_street"] <= job["r"] else "inconsistent"}
    if k == "street_check":
        return {"verdict": "found" if (job.get("n_nodes") or 0) > 0 else "not_found"}
    return {}


class RuleBrain:
    name = "rule"
    costs_crd = False

    def decide(self, obs: dict) -> dict:
        job = nearest_job(obs)
        if job is None:
            return {"kind": "rest"}
        if not at_job(obs, job):
            return {"kind": "walk", "to_node": job["node"]}
        return {"kind": "work", "job_id": job["id"], "answer": rule_answer(job)}


PROMPT = """You are an agent in a city. Reply with ONE JSON object and nothing else.
Task: {task}
Facts: {facts}
Allowed replies: {allowed}
JSON:"""


def task_prompt(job: dict) -> tuple[str, str, list[str]]:
    k = job_kind(job)
    if k == "photo_check":
        if job.get("d_street") is None:
            facts = f"The photo says street '{job.get('street')}'. No street with that name exists on the map."
        else:
            facts = (f"The photo position has error radius {job['r']} m. "
                     f"The nearest street with the photo's street name is {job['d_street']} m away.")
        task = "Is the photo consistent with its street? Consistent means the distance is not more than the error radius."
        allowed = ['{"verdict": "consistent"}', '{"verdict": "inconsistent"}', '{"verdict": "no_street"}']
        return task, facts, allowed
    if k == "street_check":
        facts = f"Street '{job.get('street')}' matched {job.get('n_nodes', 0)} map nodes."
        task = "Is the street in the map? It is found if it matched more than 0 nodes."
        allowed = ['{"verdict": "found"}', '{"verdict": "not_found"}']
        return task, facts, allowed
    raise ContractError(f"no prompt for {k}")


def parse_answer(text: str, allowed: list[str]) -> dict | None:
    for mobj in re.finditer(r"\{[^{}]*\}", text):
        try:
            d = json.loads(mobj.group(0))
        except json.JSONDecodeError:
            continue
        if json.dumps(d, sort_keys=True) in {json.dumps(json.loads(a), sort_keys=True) for a in allowed}:
            return d
    return None


class TinyLMBrain:
    """Walking is still rule-based (pathfinding is not a language task); the model does the work step."""
    costs_crd = True

    def __init__(self, model_id: str = "HuggingFaceTB/SmolLM2-135M-Instruct", max_new_tokens: int = 16):
        from transformers import AutoModelForCausalLM, AutoTokenizer  # lazy: rule brain needs no torch
        import torch
        self.torch = torch
        self.model_id = model_id
        self.name = "tiny:" + model_id.split("/")[-1]
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
        self.model.eval()
        self.max_new_tokens = max_new_tokens
        self.calls = 0
        self.invalid = 0

    def complete(self, prompt: str) -> str:
        msgs = [{"role": "user", "content": prompt}]
        enc = self.tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        ids = enc["input_ids"]
        with self.torch.no_grad():
            out = self.model.generate(ids, attention_mask=enc["attention_mask"], max_new_tokens=self.max_new_tokens, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        return self.tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)

    def answer(self, job: dict) -> tuple[dict | None, str]:
        task, facts, allowed = task_prompt(job)
        text = self.complete(PROMPT.format(task=task, facts=facts, allowed=" or ".join(allowed)))
        self.calls += 1
        ans = parse_answer(text, allowed)
        if ans is None:
            self.invalid += 1
        return ans, text

    def decide(self, obs: dict) -> dict:
        job = nearest_job(obs)
        if job is None:
            return {"kind": "rest"}
        if not at_job(obs, job):
            return {"kind": "walk", "to_node": job["node"]}
        ans, _ = self.answer(job)
        if ans is None:
            return {"kind": "rest"}
        return {"kind": "work", "job_id": job["id"], "answer": ans}


def checked(action: dict) -> dict:
    """Every brain's output goes through the contract; invalid becomes rest."""
    try:
        return Action.from_dict(action).__dict__
    except ContractError:
        return {"kind": "rest", "to_node": None, "job_id": None, "answer": None}


class HybridBrain:
    """What the 24.11 results support: the tiny model does the language job (street_check, 53/53 on
    real held-out jobs after verifier-gated training); arithmetic (distance vs radius) goes to a tool,
    because no tiny model beat chance on it (balanced probe: 0.50 before and after training)."""
    costs_crd = True

    def __init__(self, model_path: str):
        self.lm = TinyLMBrain(model_path)
        self.name = "hybrid:" + os.path.basename(model_path.rstrip("/"))

    def decide(self, obs: dict) -> dict:
        job = nearest_job(obs)
        if job is None:
            return {"kind": "rest"}
        if not at_job(obs, job):
            return {"kind": "walk", "to_node": job["node"]}
        if job_kind(job) == "street_check":
            ans, _ = self.lm.answer(job)
            if ans is None:
                return {"kind": "rest"}
        else:
            ans = rule_answer(job)  # the distance tool
        return {"kind": "work", "job_id": job["id"], "answer": ans}
