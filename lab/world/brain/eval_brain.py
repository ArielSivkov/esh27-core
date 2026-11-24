"""Score a brain on every real city job, through the contract's Verifier.

  python brain/eval_brain.py [model_id ...]

The brain sees only public_job() fields (never the verdict). Reports accuracy, invalid-output
rate, and seconds per call. Results go to brain/RESULTS_<model>.json.
"""
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "contract"))
from world_contract import public_job, truth, job_kind  # noqa: E402
from brains import TinyLMBrain, rule_answer  # noqa: E402

CITY = os.path.join(HERE, "..", "data", "city_v0.json")


def evaluate(model_id: str) -> dict:
    jobs = json.load(open(CITY))["jobs"]
    b = TinyLMBrain(model_id)
    rows, t0 = [], time.time()
    for j in jobs:
        pj = public_job(j)
        ans, raw = b.answer(pj)
        want = truth(j)
        rows.append({"id": j["id"], "kind": job_kind(j), "want": want,
                     "got": ans and ans.get("verdict"), "raw": raw[:80]})
    dt = time.time() - t0
    correct = sum(r["got"] == r["want"] for r in rows)
    by_kind = {}
    for k in sorted({r["kind"] for r in rows}):
        rs = [r for r in rows if r["kind"] == k]
        by_kind[k] = {"n": len(rs), "correct": sum(r["got"] == r["want"] for r in rs),
                      "invalid": sum(r["got"] is None for r in rs),
                      "answers": dict(Counter(str(r["got"]) for r in rs))}
    majority = Counter(truth(j) for j in jobs).most_common(1)[0]
    res = {"model": model_id, "n": len(rows), "correct": correct, "accuracy": round(correct / len(rows), 3),
           "invalid": b.invalid, "sec_per_call": round(dt / len(rows), 3), "by_kind": by_kind,
           "rule_brain_accuracy": sum(rule_answer(public_job(j)).get("verdict") == truth(j) for j in jobs) / len(jobs),
           "always_majority_baseline": {"answer": majority[0], "accuracy": round(majority[1] / len(jobs), 3)},
           "rows": rows}
    name = model_id.split("/")[-1]
    json.dump(res, open(os.path.join(HERE, f"RESULTS_{name}.json"), "w"), ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    for mid in sys.argv[1:] or ["HuggingFaceTB/SmolLM2-135M-Instruct"]:
        r = evaluate(mid)
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}, ensure_ascii=False))
