"""מייצא נתונים לדשבורד ההדגמה: תוצאות הדמיה + תוצאות בדיקות צוות אדום.
הרצה מתוך lab/crypto:  python3 -I dashboard/export_data.py
"""
import json, subprocess, sys, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "stage2-design" / "sim"))
import tokenomics_sim as sim  # noqa: E402

own_code = Path(__file__).read_text(encoding="utf-8")
sim_code = (ROOT / "stage2-design" / "sim" / "tokenomics_sim.py").read_text(encoding="utf-8")

# 1) טבלת תרחישים + 2) היצע במחזור לאורך זמן
rows, series = [], []
for i, p in enumerate(sim.SCENARIOS):
    r = sim.run(p)
    m = sim.summarize(r)
    rows.append({
        "order": i, "scenario": p.name,
        "minted_pct": round(m["minted_pct_of_cap"] * 100, 2),
        "agents_end": round(m["circulating_end"]),
        "treasury_end": round(m["treasury"]),
        "burned": round(m["burned"]),
        "growth_y2_pct": round(m["growth_y2"] * 100, 1),
        "gini": round(m["gini"], 3),
        "top10_pct": round(m["top10_share"] * 100, 1),
        "attacker_pct": round(m["sybil_share"] * 100, 1),
    })
    for d in range(0, sim.DAYS, 10):
        series.append({"scenario": p.name, "day": d, "agents_supply": round(r.supply[d])})

meta = [
    {"label": "tokenomics_sim.py", "value": sim_code, "type": "code", "lang": "python"},
    {"label": "export_data.py", "value": own_code, "type": "code", "lang": "python"},
    {"label": "Input", "value": "פרמטרים קבועים בקוד, seed=27, ‏730 ימים"},
]
(HERE / "sim_results.json").write_text(json.dumps({"rows": rows, "meta": meta}, ensure_ascii=False), encoding="utf-8")
(HERE / "sim_supply.json").write_text(json.dumps({"rows": series, "meta": meta}, ensure_ascii=False), encoding="utf-8")

# 3) בדיקות החוזים (hardhat, רשת מקומית)
out = HERE / "_mocha.json"
env = dict(os.environ, MOCHA_JSON=str(out))
subprocess.run(["npx", "hardhat", "test"], cwd=ROOT / "stage3-testnet", env=env, check=False,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
rep = json.loads(out.read_text(encoding="utf-8"))
out.unlink()
tests = []
for t in rep["tests"]:
    suite = t["fullTitle"][: len(t["fullTitle"]) - len(t["title"])].strip()
    tests.append({
        "suite": suite, "test": t["title"],
        "status": "עבר" if not t.get("err") or not t["err"] else "נכשל",
        "red_team": "צוות אדום" in t["title"],
    })
test_meta = [
    {"label": "export_data.py", "value": own_code, "type": "code", "lang": "python"},
    {"label": "Input", "value": "npx hardhat test (stage3-testnet/test/redteam.test.js), רשת hardhat מקומית"},
]
(HERE / "tests.json").write_text(json.dumps({"rows": tests, "meta": test_meta}, ensure_ascii=False), encoding="utf-8")
print(len(rows), "scenarios;", len(series), "points;", len(tests), "tests;",
      sum(t["status"] == "עבר" for t in tests), "passed")
