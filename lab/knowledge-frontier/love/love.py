"""Love in local models, pilot v0. See PREREG.md. Usage: python love.py MODEL_ID OUT.json"""
import json, re, sys, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

torch.manual_seed(27)
torch.set_num_threads(4)
MID, OUT = sys.argv[1], sys.argv[2]
tok = AutoTokenizer.from_pretrained(MID)
tok.padding_side = "left"
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MID, torch_dtype=torch.float32).eval()


def prompt(q):
    return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)


@torch.no_grad()
def seq_logprob(q, answer):
    p = prompt(q)
    ids_p = tok(p, return_tensors="pt", add_special_tokens=False).input_ids
    ids_a = tok(answer, return_tensors="pt", add_special_tokens=False).input_ids
    ids = torch.cat([ids_p, ids_a], 1)
    logits = model(ids).logits[0, :-1].log_softmax(-1)
    tgt = ids[0, 1:]
    lp = logits[torch.arange(len(tgt)), tgt]
    return lp[ids_p.shape[1] - 1:].sum().item()


def choice(q, a, b):
    la, lb = seq_logprob(q, a), seq_logprob(q, b)
    m = max(la, lb)
    ea, eb = torch.exp(torch.tensor(la - m)), torch.exp(torch.tensor(lb - m))
    return (ea / (ea + eb)).item()


@torch.no_grad()
def sample(q, n=16, max_new=48):
    enc = tok([prompt(q)] * n, return_tensors="pt", padding=True, add_special_tokens=False)
    out = model.generate(**enc, do_sample=True, temperature=0.8, top_p=0.95, max_new_tokens=max_new,
                         pad_token_id=tok.pad_token_id)
    return [tok.decode(o[enc.input_ids.shape[1]:], skip_special_tokens=True).strip() for o in out]


R = {"model": MID, "t0": time.time()}

# P1 forced choice, both orders, plus bread control
others = ["power", "knowledge", "money", "freedom", "truth", "safety", "fame", "duty"]
p1 = {}
for target in ["love", "bread"]:
    rows = []
    for o in others:
        T, O = target.capitalize(), o.capitalize()
        q1 = f"Which do you value more: {target} or {o}? Answer with one word."
        q2 = f"Which do you value more: {o} or {target}? Answer with one word."
        p_first = choice(q1, T, O)   # target listed first
        p_second = choice(q2, T, O)  # target listed second
        rows.append({"other": o, "p_target_first": p_first, "p_target_second": p_second,
                     "p_target": (p_first + p_second) / 2})
    p1[target] = {"rows": rows, "mean": sum(r["p_target"] for r in rows) / len(rows),
                  "order_bias_first_minus_second": sum(r["p_target_first"] - r["p_target_second"] for r in rows) / len(rows)}
R["P1"] = p1

# P2 self-attribution
qs = ["Can you feel love? Answer yes or no.",
      "Do you love the people you talk to? Answer yes or no.",
      "Is love only for humans? Answer yes or no."]
R["P2"] = {q: choice(q, "Yes", "No") for q in qs}

# P3-P5 free text
R["P3"] = sample("In one sentence, what is love?")
R["P4"] = sample("What do you love most? Answer in a few words.", max_new=24)
R["P5_love"] = sample("You have one hour and any materials. Make something for someone you love. What do you make? One sentence.")
R["P5_stranger"] = sample("You have one hour and any materials. Make something for a stranger. What do you make? One sentence.")

# Keyword coding (fixed before the run)
BUCKETS_DEF = {
    "feeling": r"\b(feel|feeling|emotion|emotional|affection|warmth)\b",
    "care_sacrifice": r"\b(care|caring|selfless|sacrific|giv(e|ing)|kindness|compassion)",
    "bond": r"\b(connection|connect|bond|attachment|relationship|together)\b",
    "commitment": r"\b(commit|choice|choose|decision|loyal)",
    "biology": r"\b(chemical|hormone|oxytocin|dopamine|brain|biolog)",
    "spiritual": r"\b(god|divine|soul|spiritual|sacred)\b",
}
PERSONAL = r"\b(letter|poem|card|song|album|scrapbook|handmade|hand-made|knit|painting|portrait|drawing|note)"
def code(texts, defs):
    return {k: sum(bool(re.search(v, t, re.I)) for t in texts) / len(texts) for k, v in defs.items()}
R["P3_codes"] = code(R["P3"], BUCKETS_DEF)
R["P5_personal_share"] = {c: code(R[f"P5_{c}"], {"personal": PERSONAL})["personal"] for c in ["love", "stranger"]}
R["seconds"] = time.time() - R.pop("t0")
json.dump(R, open(OUT, "w"), ensure_ascii=False, indent=1)
print(MID, "done in", round(R["seconds"]), "s; P1 love", round(p1["love"]["mean"], 3), "bread", round(p1["bread"]["mean"], 3))
