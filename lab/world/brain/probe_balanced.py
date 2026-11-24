"""Balanced synthetic probe (SYNTHETIC, not city data): half the photo jobs are inconsistent.
Answers are computed by the rule (d_street <= r). Tests whether a small brain compares numbers or just says yes."""
import json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from brains import TinyLMBrain, rule_answer
rnd = random.Random(27)
jobs = []
for i in range(40):
    r = round(rnd.uniform(15, 50), 1)
    d = round(r * rnd.uniform(0.2, 0.9), 1) if i % 2 == 0 else round(r * rnd.uniform(1.3, 4.0), 1)
    jobs.append({"id": f"S{i:02d}", "job_kind": "photo_check", "node": 0, "x": 0, "y": 0, "street": "הארז", "r": r, "d_street": d})
out = {}
for mid in sys.argv[1:]:
    b = TinyLMBrain(mid); got = [ (b.answer(j)[0] or {}).get("verdict") for j in jobs ]
    want = [rule_answer(j)["verdict"] for j in jobs]
    out[mid] = {"accuracy": sum(g == w for g, w in zip(got, want)) / len(jobs), "said_consistent": got.count("consistent"),
                "said_inconsistent": got.count("inconsistent"), "invalid": got.count(None), "n": len(jobs), "half_are_inconsistent": True}
    print(json.dumps({mid: out[mid]}))
json.dump(out, open(os.path.join(HERE, "RESULTS_probe_balanced.json"), "w"), indent=1)
