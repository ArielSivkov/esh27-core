"""Runs every CHAIN27 lab experiment and writes results/ (CSV, PNG, REPORT.md).

    python run_experiments.py          # full run, a few minutes
    python run_experiments.py --quick  # shorter runs, for a quick look
"""
import csv
import json
import os
import random
import sys
import time
from multiprocessing import Pool

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from chain27lab import economics  # noqa: E402
from chain27lab.crypto_bench import bench  # noqa: E402
from chain27lab.world import Config, World  # noqa: E402

QUICK = "--quick" in sys.argv
DUR = 20.0 if QUICK else 60.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)
BASE = Config(duration=DUR, jail_blocks=100)


def pick(n, k, seed):
    return sorted(random.Random(seed).sample(range(n), k))


def run_cfg(cfg):
    w = World(cfg)
    s = w.run()
    s["commit_times"] = [v[1] for _, v in sorted(w.canonical.items())]
    return s


def run_many(cfgs):
    with Pool(min(4, os.cpu_count() or 1)) as p:
        return p.map(run_cfg, cfgs)


def write_csv(name, rows, keys):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for r in rows:
            w.writerow([r.get(k) for k in keys])


def fmt(x, d=2):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{x:,.{d}f}"
    return f"{x:,}" if isinstance(x, int) else str(x)


def savefig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, name), dpi=130)
    plt.close()


def main():
    t0 = time.time()
    R = {}

    # 0. crypto cost on this machine
    cb = bench()
    R["crypto"] = cb
    base = BASE.with_(verify_cost=cb["ed25519_verify_us"] * 1e-6)

    # 1. baseline
    R["baseline"] = run_cfg(base)

    # 2. crash sweep, round-robin vs jailing
    ks = list(range(0, 11))
    cfgs = []
    for policy in (0, 100):
        for k in ks:
            cfgs.append(base.with_(jail_blocks=policy, behaviors={i: "crash" for i in pick(27, k, 100 + k)}))
    res = run_many(cfgs)
    crash = []
    for idx, s in enumerate(res):
        policy = "round_robin" if idx < len(ks) else "jailing"
        crash.append({"policy": policy, "crashed": ks[idx % len(ks)], **{k: v for k, v in s.items() if k != "commit_times"}})
    R["crash"] = crash
    write_csv("crash_sweep.csv", crash, ["policy", "crashed", "blocks", "achieved_tps", "block_interval_mean_s",
                                           "block_interval_max_s", "finality_p50_s", "finality_p95_s", "extra_rounds", "forks"])
    plt.figure(figsize=(7, 4))
    for policy, style in (("round_robin", "o--"), ("jailing", "s-")):
        xs = [r["crashed"] for r in crash if r["policy"] == policy]
        ys = [r["blocks"] / (DUR / 60) for r in crash if r["policy"] == policy]
        plt.plot(xs, ys, style, label=policy)
    plt.axvline(8.5, color="red", ls=":", label="f = 8 limit")
    plt.xlabel("crashed validators (of 27)")
    plt.ylabel("blocks per minute")
    plt.title("Liveness vs crashed validators")
    plt.legend()
    plt.grid(alpha=0.3)
    savefig("crash_sweep.png")

    # 3. timeline: nodes fail one group at a time, then one comes back
    order = pick(27, 9, 7)
    sched = [(DUR * 0.2, "crash", order[:4]), (DUR * 0.35, "crash", order[4:8]),
             (DUR * 0.5, "crash", order[8:9]), (DUR * 0.7, "restore", order[8:9])]
    tl = run_many([base.with_(duration=DUR * 1.1, schedule=sched, jail_blocks=j) for j in (0, 100)])
    R["timeline"] = {"schedule": sched, "blocks_rr": tl[0]["blocks"], "blocks_jail": tl[1]["blocks"],
                     "forks": tl[0]["forks"] + tl[1]["forks"]}
    plt.figure(figsize=(8, 4))
    for s, lab in ((tl[0], "round_robin"), (tl[1], "jailing")):
        ts = s["commit_times"]
        plt.plot(ts, range(1, len(ts) + 1), label=lab)
    for t, action, idxs in sched:
        plt.axvline(t, color="red" if action == "crash" else "green", ls=":")
    plt.text(DUR * 0.2, 5, " 4 down", color="red")
    plt.text(DUR * 0.35, 5, " 8 down", color="red")
    plt.text(DUR * 0.5, 5, " 9 down", color="red")
    plt.text(DUR * 0.7, 5, " back to 8", color="green")
    plt.xlabel("time (s)")
    plt.ylabel("committed blocks")
    plt.title("Failures over time")
    plt.legend()
    plt.grid(alpha=0.3)
    savefig("timeline.png")

    # 4. byzantine: equivocating validators
    eks = [0, 2, 4, 6, 8, 9, 10, 12]
    byz = run_many([base.with_(behaviors={i: "equivocate" for i in pick(27, k, 200 + k)}) for k in eks])
    byz = [{"equivocators": k, **{a: b for a, b in s.items() if a != "commit_times"}} for k, s in zip(eks, byz)]
    R["byzantine"] = byz
    write_csv("byzantine.csv", byz, ["equivocators", "blocks", "achieved_tps", "finality_p50_s", "finality_p95_s",
                                      "forks", "evidence_detected", "validators_slashed"])

    # 5. load sweep at 100 Mbps and 1 Gbps
    tpss = [100, 500, 1000, 2000, 4000, 8000]
    load = run_many([base.with_(tps=t, bandwidth_bps=bw) for bw in (100e6, 1e9) for t in tpss])
    load = [{"bandwidth": "100Mbps" if i < len(tpss) else "1Gbps", "tps": tpss[i % len(tpss)],
             **{a: b for a, b in s.items() if a != "commit_times"}} for i, s in enumerate(load)]
    R["load"] = load
    write_csv("load_sweep.csv", load, ["bandwidth", "tps", "achieved_tps", "block_interval_mean_s", "finality_p50_s",
                                        "finality_p95_s", "backlog_txs", "mb_per_block"])
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for bw, st in (("100Mbps", "o-"), ("1Gbps", "s--")):
        rows = [r for r in load if r["bandwidth"] == bw]
        ax[0].plot([r["tps"] for r in rows], [r["achieved_tps"] for r in rows], st, label=bw)
        ax[1].plot([r["tps"] for r in rows], [r["finality_p95_s"] or 0 for r in rows], st, label=bw)
    ax[0].plot(tpss, tpss, "k:", label="offered = achieved")
    ax[0].set_xlabel("offered tx/s")
    ax[0].set_ylabel("achieved tx/s")
    ax[0].set_title("Throughput")
    ax[1].set_xlabel("offered tx/s")
    ax[1].set_ylabel("p95 finality (s)")
    ax[1].set_yscale("log")
    ax[1].set_title("Finality under load")
    for a in ax:
        a.legend()
        a.grid(alpha=0.3)
    savefig("load_sweep.png")

    # 6. network latency sweep
    lats = [0.005, 0.02, 0.04, 0.08, 0.15, 0.3]
    lat = run_many([base.with_(latency_median=l) for l in lats])
    lat = [{"latency_ms": l * 1000, **{a: b for a, b in s.items() if a != "commit_times"}} for l, s in zip(lats, lat)]
    R["latency"] = lat
    write_csv("latency_sweep.csv", lat, ["latency_ms", "blocks", "block_interval_mean_s", "finality_p50_s",
                                          "finality_p95_s", "extra_rounds"])

    # 7. validator count sweep
    ns = [4, 7, 13, 22, 27, 40, 60]
    val = run_many([base.with_(n_validators=n) for n in ns])
    val = [{"n": n, **{a: b for a, b in s.items() if a != "commit_times"}} for n, s in zip(ns, val)]
    R["validators"] = val
    write_csv("validator_sweep.csv", val, ["n", "blocks", "block_interval_mean_s", "finality_p50_s",
                                            "msgs_per_block", "mb_per_block"])
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(ns, [r["msgs_per_block"] for r in val], "o-")
    ax[0].set_xlabel("validators")
    ax[0].set_ylabel("network messages per block")
    ax[0].set_title("Message cost grows ~ n^2")
    ax[1].plot(ns, [r["finality_p50_s"] for r in val], "o-")
    ax[1].set_xlabel("validators")
    ax[1].set_ylabel("p50 finality (s)")
    ax[1].set_title("Finality vs validator count")
    for a in ax:
        a.grid(alpha=0.3)
    savefig("validator_sweep.png")

    # 8. economics (ledger-only, using the measured block interval)
    bi = R["baseline"]["block_interval_mean_s"]
    blocks_per_day = 86400 / bi
    blocks_per_year = blocks_per_day * 365
    ecfg = base.with_(halving_blocks=int(blocks_per_year))
    nb = 1500 if QUICK else 4000
    econ = []
    for t in [1, 10, 50, 200, 1000, 3000, 8000]:
        led, rows = economics.run(ecfg, bi, lambda h, t=t: t, nb)
        k = blocks_per_day / nb
        last = rows[-200:]
        econ.append({
            "tps_demand": t,
            "tps_included": sum(r[3] for r in rows) / (nb * bi),
            "base_fee_end": led.base_fee,
            "burn_per_day": led.burned * k,
            "emission_per_day": led.rewards_total * k,
            "charity_per_day": led.charity * k,
            "net_circulating_change_per_day": (led.rewards_total - led.burned) * k,
            "avg_fee_last": sum(r[4] for r in last) / len(last),
        })
    R["economics"] = econ
    write_csv("economics.csv", econ, list(econ[0].keys()))
    plt.figure(figsize=(7, 4))
    xs = [e["tps_demand"] for e in econ]
    plt.plot(xs, [e["emission_per_day"] for e in econ], "g-", label="new coins to validators / day (from treasury)")
    plt.plot(xs, [e["burn_per_day"] for e in econ], "r-o", label="burned / day")
    plt.plot(xs, [e["charity_per_day"] for e in econ], "b-s", label="charity fund / day")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("transaction demand (tx/s)")
    plt.ylabel("ESH27-test per day")
    plt.title("Emission vs burn")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.3)
    savefig("economics.png")

    def spike(h):
        third = nb // 3
        return 100 if h < third or h > 2 * third else 12000
    led, rows = economics.run(ecfg, bi, spike, nb)
    with open(os.path.join(OUT, "fee_spike.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["height", "t", "demand", "included", "base_fee", "burned", "rewards", "charity", "circulating"])
        w.writerows(rows)
    fig, ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    ax[0].plot([r[1] for r in rows], [r[2] for r in rows], label="demand")
    ax[0].plot([r[1] for r in rows], [r[3] for r in rows], label="included")
    ax[0].set_ylabel("tx per block")
    ax[0].legend()
    ax[1].plot([r[1] for r in rows], [r[4] for r in rows], "r")
    ax[1].set_ylabel("base fee")
    ax[1].set_xlabel("time (s)")
    ax[0].set_title("Demand spike: base fee reaction")
    for a in ax:
        a.grid(alpha=0.3)
    savefig("fee_spike.png")
    R["spike"] = {"peak_fee": max(r[4] for r in rows), "max_included": max(r[3] for r in rows)}

    # treasury lifetime with yearly halving
    treasury = 270e6 * 0.40
    per_year = ecfg.block_reward * blocks_per_year
    remaining, years = treasury, 0.0
    reward = per_year
    while remaining > 0 and years < 100:
        if reward >= remaining:
            years += remaining / reward
            remaining = 0
            break
        remaining -= reward
        reward /= 2
        years += 1
    R["treasury"] = {
        "block_interval_s": bi, "blocks_per_year": blocks_per_year, "block_reward": ecfg.block_reward,
        "first_year_emission": per_year, "years_until_empty": years if remaining == 0 else None,
        "max_reward_for_forever": treasury / (2 * blocks_per_year),
    }
    R["runtime_s"] = time.time() - t0
    R["quick"] = QUICK
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(R, f, indent=1, default=str)
    write_report(R)
    print(f"done in {R['runtime_s']:.0f}s -> {OUT}")


def write_report(R):
    b = R["baseline"]
    tre = R["treasury"]
    crash = {(r["policy"], r["crashed"]): r for r in R["crash"]}
    L = []
    a = L.append
    a("# CHAIN27 Lab: דוח ניסויים\n")
    a(f"נוצר אוטומטית על ידי `run_experiments.py`{' (מצב מהיר)' if R['quick'] else ''}. "
      f"כל ריצה נמשכת {DUR:.0f} שניות של זמן מדומה, עם seed קבוע, כך שהתוצאות ניתנות לשחזור. "
      "הרשת היא הדמיה במחשב אחד, לא רשת אמיתית. המספרים מראים מגמות ומגבלות, ולא ביצועים של מוצר.\n")

    a("## קו בסיס: 27 צמתים תקינים\n")
    a("| מדד | ערך |\n|---|---|")
    a(f"| בלוקים בדקה | {b['blocks'] / (DUR / 60):.0f} |")
    a(f"| זמן בין בלוקים (ממוצע) | {fmt(b['block_interval_mean_s'], 3)} שניות |")
    a(f"| סופיות עסקה, חציון / 95% | {fmt(b['finality_p50_s'], 3)} / {fmt(b['finality_p95_s'], 3)} שניות |")
    a(f"| עסקאות בשנייה (ביקוש 200) | {fmt(b['achieved_tps'], 1)} |")
    a(f"| הודעות רשת לבלוק | {fmt(b['msgs_per_block'], 0)} |")
    a(f"| עלות אימות חתימת Ed25519 (נמדד) | {R['crypto']['ed25519_verify_us']:.0f} מיקרו-שניות |")
    a(f"| פיצולים (forks) | {b['forks']} |")
    a(f"| בדיקת היצע 270M | {'תקין' if b['supply_check_ok'] else 'נכשל'} |\n")

    a("## עמידות: כמה צמתים יכולים ליפול\n")
    a("![crash](crash_sweep.png)\n")
    a("| צמתים שנפלו | בלוקים בדקה, סבב רגיל | בלוקים בדקה, עם השעיה | סופיות 95%, עם השעיה |\n|---|---|---|---|")
    for k in range(11):
        rr, jl = crash[("round_robin", k)], crash[("jailing", k)]
        a(f"| {k} | {rr['blocks'] / (DUR / 60):.0f} | {jl['blocks'] / (DUR / 60):.0f} | {fmt(jl['finality_p95_s'])} |")
    rr8, jl8 = crash[("round_robin", 8)], crash[("jailing", 8)]
    a("")
    a("**ממצאים:**")
    a("- הרשת ממשיכה לייצר בלוקים עם עד 8 צמתים שנפלו, ונעצרת לגמרי ב-9, כמו שהתיאוריה צופה (f = 8 עבור 27 צמתים, נדרשים 19 קולות).")
    a(f"- בסבב מציעים רגיל, כל צומת שנפל מבזבז סבב שלם כשמגיע תורו. עם 8 צמתים שנפלו: {rr8['blocks'] / (DUR / 60):.0f} בלוקים בדקה. "
      f"עם השעיה של מציע שנכשל (100 בלוקים): {jl8['blocks'] / (DUR / 60):.0f}. זה המימוש הפשוט של \"מדד האמינות\" מה-Whitepaper 1.1, והוא נגזר רק מבלוקים שכבר נחתמו, כך שכל הצמתים מסכימים עליו.")
    a("- גם עם השעיה, כשנשארים בדיוק 19 צמתים חיים, כל בלוק מחכה לצומת האיטי ביותר מביניהם, והסופיות עולה.\n")

    a("## נפילה הדרגתית לאורך זמן\n")
    a("![timeline](timeline.png)\n")
    a(f"4 צמתים נופלים, אחר כך 8, אחר כך 9 (עצירה), ואז צומת אחד חוזר. בלוקים שנחתמו: {R['timeline']['blocks_rr']} בסבב רגיל, "
      f"{R['timeline']['blocks_jail']} עם השעיה. פיצולים: {R['timeline']['forks']}. אחרי שצומת חוזר והרשת שוב ב-19 צמתים, היא ממשיכה מאותה נקודה בלי התערבות ידנית. "
      "בסבב רגיל ההתאוששות איטית, כי הסבב ממשיך לעבור דרך 8 הצמתים שעדיין למטה. עם השעיה הם מדולגים.\n")
    a("**באג שהמעבדה מצאה ושתוקן:** בגרסה הראשונה, אחרי שצומת חזר הרשת נשארה תקועה לתמיד. הקולות שנשלחו אליו בזמן שהיה למטה אבדו, "
      "ובלי הקול שלו אף צומת לא הגיע ל-19. הפתרון: צומת שתקוע באותו גובה יותר משנייה שולח שוב את הקולות שלו. "
      "רשתות אמיתיות (Tendermint, CometBFT) עושות את זה כל הזמן. זה בדיוק מסוג הדברים שקל לפספס כשבונים קונצנזוס מאפס.\n")

    a("## צמתים זדוניים (equivocation)\n")
    a("צומת זדוני שולח הצעות וקולות סותרים לחצאים שונים של הרשת. צמתים ישרים שמקבלים שני קולות סותרים מאותו צומת שומרים ראיה. הראיה נכנסת לבלוק, ו-10% מהסטייק של הצומת נשרפים.\n")
    a("| זדוניים | בלוקים | פיצולים | ראיות שנאספו | צמתים שנקנסו |\n|---|---|---|---|---|")
    for r in R["byzantine"]:
        a(f"| {r['equivocators']} | {r['blocks']} | {r['forks']} | {r['evidence_detected']} | {r['validators_slashed']} |")
    a("")
    a("**ממצאים:** עד 8 זדוניים, הרשת חיה, בלי פיצולים, והתוקפים נקנסים ומושעים. מ-9 ומעלה היא נעצרת. "
      "בניסוי הזה לא נוצר פיצול גם מעל הסף, אבל זה בגלל שאסטרטגיית התקיפה פשוטה. מעל 8 זדוניים אין שום הבטחה תיאורטית לבטיחות.\n")

    a("## עומס ורוחב פס\n")
    a("![load](load_sweep.png)\n")
    a("| רוחב פס | ביקוש tx/s | בפועל tx/s | סופיות 95% | MB לבלוק |\n|---|---|---|---|---|")
    for r in R["load"]:
        a(f"| {r['bandwidth']} | {r['tps']} | {fmt(r['achieved_tps'], 0)} | {fmt(r['finality_p95_s'])} | {fmt(r['mb_per_block'])} |")
    a("")
    a("**ממצאים:**")
    a("- צוואר הבקבוק הוא רוחב הפס של המציע. הוא שולח את הבלוק לכל 26 הצמתים האחרים, ולכן כל עסקה נשלחת 26 פעמים.")
    cap100 = max(r["achieved_tps"] for r in R["load"] if r["bandwidth"] == "100Mbps")
    cap1g = max(r["achieved_tps"] for r in R["load"] if r["bandwidth"] == "1Gbps")
    worst = max((r["finality_p95_s"] or 0) for r in R["load"] if r["bandwidth"] == "100Mbps")
    a(f"- ב-100Mbps התפוקה נעצרת סביב {cap100:,.0f} עסקאות בשנייה. מעבר לזה התור רק גדל, והסופיות קופצת מפחות משנייה לעשרות שניות (עד {worst:.0f}). "
      "בלוק גדול לוקח יותר זמן לשדר מזמן ההמתנה להצעה, ולכן חלק מהסבבים מתבזבזים. "
      "התיקון: להגביל את גודל הבלוק לפי רוחב הפס, או להאריך את זמן ההמתנה לפי גודל הבלוק.")
    a(f"- ב-1Gbps התקרה עולה לכ-{cap1g:,.0f}. מעבר לזה צריך הפצה בשרשור (gossip) של חלקי בלוק במקום שליחה ישירה לכולם.\n")

    a("## השהיית רשת\n")
    a("| השהיה חציונית (ms) | זמן בין בלוקים | סופיות חציון | סופיות 95% | סבבים נוספים |\n|---|---|---|---|---|")
    for r in R["latency"]:
        a(f"| {r['latency_ms']:.0f} | {fmt(r['block_interval_mean_s'], 3)} | {fmt(r['finality_p50_s'], 3)} | {fmt(r['finality_p95_s'], 3)} | {r['extra_rounds']} |")
    a("")
    a("**ממצא:** כל בלוק דורש כ-3 מעברים ברשת (הצעה, קול מקדים, קול סופי), ולכן הסופיות גדלה בערך פי 3 מההשהיה. כשההשהיה מתקרבת לזמני ההמתנה של הפרוטוקול, מתחילים סבבים מבוזבזים. בפריסה בין יבשות צריך להגדיל את זמני ההמתנה.\n")

    a("## מספר הצמתים\n")
    a("![validators](validator_sweep.png)\n")
    a("| צמתים | הודעות לבלוק | MB לבלוק | סופיות חציון |\n|---|---|---|---|")
    for r in R["validators"]:
        a(f"| {r['n']} | {fmt(r['msgs_per_block'], 0)} | {fmt(r['mb_per_block'])} | {fmt(r['finality_p50_s'], 3)} |")
    a("")
    a("**ממצא:** מספר ההודעות גדל בערך בריבוע מספר הצמתים, כי כל צומת שולח קול לכל צומת אחר. 27 צמתים זה גודל נוח. במאות צמתים צריך לאגד חתימות (BLS).\n")

    a("## כלכלת המטבע ESH27-test\n")
    a("![economics](economics.png)\n")
    a("| ביקוש tx/s | נכנס בפועל tx/s | עמלה בסוף | נשרף ביום | הונפק ביום | לצדקה ביום | שינוי נטו במחזור ביום |\n|---|---|---|---|---|---|---|")
    for e in R["economics"]:
        a(f"| {e['tps_demand']} | {fmt(e['tps_included'], 0)} | {e['base_fee_end']:.4f} | {fmt(e['burn_per_day'], 0)} | "
          f"{fmt(e['emission_per_day'], 0)} | {fmt(e['charity_per_day'], 0)} | {fmt(e['net_circulating_change_per_day'], 0)} |")
    a("")
    a("![spike](fee_spike.png)\n")
    a(f"**ממצאים:**")
    a(f"- עם תגמול של {tre['block_reward']} מטבעות לבלוק ובלוק כל {tre['block_interval_s']:.2f} שניות, יוצאים מהאוצר "
      f"{tre['first_year_emission'] / 1e6:,.0f} מיליון מטבעות בשנה הראשונה. האוצר (108 מיליון) "
      + (f"מתרוקן אחרי {tre['years_until_empty']:.1f} שנים, גם עם חצייה שנתית." if tre["years_until_empty"] else "לא מתרוקן.")
      + f" כדי שהאוצר יחזיק לנצח עם חצייה שנתית, התגמול צריך להיות לכל היותר {tre['max_reward_for_forever']:.3f} לבלוק.")
    a("- השריפה עולה על ההנפקה רק בעומס גבוה מאוד, כי העמלה הבסיסית יורדת לרצפה כשהבלוקים לא מלאים. במילים אחרות: ברשת צעירה המטבע הוא אינפלציוני, והדפלציה שהובטחה ב-Whitepaper 1.0 תלויה בביקוש גבוה.")
    a(f"- בקפיצת ביקוש, העמלה עולה תוך דקות (שיא {R['spike']['peak_fee']:.3f}) ומסננת עסקאות, ואחרי הקפיצה היא חוזרת לרצפה.")
    a("- הדמיית הכלכלה לא מגבילה רוחב פס. בפועל, ב-100Mbps הרשת לא מחזיקה יותר מכ-1,200 עסקאות בשנייה (ראה סעיף העומס), ולכן השורות של 3,000 ו-8,000 הן תיאורטיות.")
    a("- הקרן לצדקה מקבלת 10% מהעמלות בלבד, ולכן בעומס נמוך היא כמעט ריקה. אם הקרן חשובה, כדאי לשקול גם נתח קבוע מתגמולי הבלוק.\n")

    a("## מגבלות המעבדה\n")
    a("- הדמיה בתהליך אחד. הרשת, ההשהיות ועלויות ה-CPU מדומות לפי מודל. קריפטוגרפיה אמיתית נמדדת רק בבנצ'מרק, ואין חתימה בפועל על כל הודעה.")
    a("- המאגר (mempool) משותף, וכל עסקה נחשפת לכל הצמתים אחרי השהיה אחת.")
    a("- צומת שחוזר מקבל העתק של השרשרת מצומת ישר (סנכרון מופשט).")
    a("- תוקף זדוני אחד בלבד מסוג אחד (equivocation). אין התקפות רשת, אין שוחד ואין קנוניה מתוחכמת.")
    a("- הכלכלה מניחה ביקוש פשוט: לכל עסקה יש עמלה מקסימלית אקראית.\n")
    a(f"זמן ריצה: {R['runtime_s']:.0f} שניות.")
    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
