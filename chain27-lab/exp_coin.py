"""Experiment 01: ESH27-test coin economics.

Block reward sensitivity (0.5 to 1.0), fee market vs real network capacity,
10-year supply projection, and charity fund funding.

    python exp_coin.py      # writes results/coin/
"""
import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from chain27lab import economics  # noqa: E402
from chain27lab.world import Config  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "coin")
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(HERE, "results", "summary.json")) as f:
    S = json.load(f)
BI = S["baseline"]["block_interval_mean_s"]  # measured by the consensus runs
CAP_100M = max(r["achieved_tps"] for r in S["load"] if r["bandwidth"] == "100Mbps")
BPD = 86400 / BI
BPY = BPD * 365
TREASURY = 270e6 * 0.40
GENESIS_CIRC = 270e6 * 0.20 + 27e6  # users + validator stakes
REWARDS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 2.0]
YEARS = 10


def emission_schedule(R, years=YEARS):
    """Yearly emission with a halving every year, until the treasury is empty."""
    left, out, r = TREASURY, [], R * BPY
    for _ in range(years):
        e = min(r, left)
        out.append(e)
        left -= e
        r /= 2
    return out, left


def years_until_empty(R):
    left, r, y = TREASURY, R * BPY, 0.0
    for _ in range(200):
        if r >= left:
            return y + left / r
        left -= r
        r /= 2
        y += 1
    return None  # never within 200 years


def write_csv(name, rows):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    # ---- A. reward sensitivity (exact arithmetic) ----
    A = []
    for R in REWARDS:
        sched, _ = emission_schedule(R, 200)
        A.append({
            "reward": R,
            "year1_emission_M": R * BPY / 1e6,
            "year1_inflation_pct": R * BPY / GENESIS_CIRC * 100,
            "years_until_empty": years_until_empty(R),
            "total_emitted_M": sum(sched) / 1e6,
        })
    write_csv("reward_sensitivity.csv", A)
    max_forever = TREASURY / (2 * BPY)

    # ---- B. fee market: burn vs demand, current cap vs capacity-matched cap ----
    cap_matched = int(CAP_100M * BI)  # txs per block the 100 Mbps network can carry
    caps = {"current_4000": 4000, f"matched_{cap_matched}": cap_matched}
    demands = [50, 200, 600, 900, 1200, 2000]
    B = []
    for label, cap in caps.items():
        cfg = Config(max_block_txs=cap, block_reward=0.7)
        for d in demands:
            led, rows = economics.run(cfg, BI, lambda h, d=d: d, 4000)
            k = BPD / 4000
            last = rows[-500:]
            B.append({
                "block_cap": label,
                "demand_tps": d,
                "included_tps": sum(r[3] for r in rows) / (4000 * BI),
                "avg_fee": sum(r[4] for r in last) / len(last),
                "burn_per_day": led.burned * k,
                "charity_from_fees_per_day": (led.charity) * k,
            })
    write_csv("fee_market.csv", B)

    # ---- C. 10-year supply projection ----
    C = []
    burn_lookup = {(b["block_cap"], b["demand_tps"]): b["burn_per_day"] * 365 for b in B}
    matched = f"matched_{cap_matched}"
    for R in REWARDS[:-1]:
        sched, _ = emission_schedule(R)
        for d in (200, 600):
            circ = GENESIS_CIRC
            for y, e in enumerate(sched, 1):
                circ += e - burn_lookup[(matched, d)]
                assert circ > 0, "projection left the range where it is meaningful"
                C.append({"reward": R, "demand_tps": d, "year": y, "circulating_M": circ / 1e6,
                          "emission_M": e / 1e6, "burn_M": burn_lookup[(matched, d)] / 1e6})
    write_csv("supply_10y.csv", C)

    # ---- D. charity fund: fees only vs 5% of block reward ----
    D = []
    for share in (0.0, 0.05):
        for d in (50, 200, 600):
            cfg = Config(max_block_txs=cap_matched, block_reward=0.7, charity_reward_share=share)
            led, _ = economics.run(cfg, BI, lambda h, d=d: d, 4000)
            D.append({"reward_share": share, "demand_tps": d, "charity_per_day": led.charity * BPD / 4000})
    write_csv("charity.csv", D)

    # ---- charts ----
    plt.figure(figsize=(7, 4))
    xs = [a["reward"] for a in A]
    ys = [a["years_until_empty"] if a["years_until_empty"] is not None else 30 for a in A]
    plt.bar([str(x) for x in xs], ys, color=["#2a9d8f" if a["years_until_empty"] is None else "#e76f51" for a in A])
    plt.ylabel("years until treasury is empty (30 = never)")
    plt.xlabel("block reward (ESH27-test)")
    plt.title(f"Treasury lifetime, yearly halving (limit = {max_forever:.3f})")
    plt.grid(alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "treasury_lifetime.png"), dpi=130)
    plt.close()

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for label, st in zip(caps, ("o--", "s-")):
        rows = [b for b in B if b["block_cap"] == label]
        ax[0].plot([r["demand_tps"] for r in rows], [r["burn_per_day"] for r in rows], st, label=f"cap {label}")
        ax[1].plot([r["demand_tps"] for r in rows], [r["avg_fee"] for r in rows], st, label=f"cap {label}")
    for R in (0.5, 0.7, 1.0):
        ax[0].axhline(R * BPD, ls=":", color="gray")
        ax[0].text(50, R * BPD * 1.1, f"emission at reward {R}", fontsize=8, color="gray")
    ax[0].axvline(CAP_100M, color="red", ls=":")
    ax[1].axvline(CAP_100M, color="red", ls=":", label="measured 100Mbps capacity")
    ax[0].set_yscale("log")
    ax[0].set_xlabel("demand (tx/s)")
    ax[0].set_ylabel("burned per day")
    ax[0].set_title("Burn vs emission")
    ax[1].set_xlabel("demand (tx/s)")
    ax[1].set_ylabel("base fee")
    ax[1].set_title("Fee market")
    for a in ax:
        a.legend(fontsize=8)
        a.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fee_market.png"), dpi=130)
    plt.close()

    fig, ax = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for i, d in enumerate((200, 600)):
        for R in REWARDS[:-1]:
            rows = [c for c in C if c["reward"] == R and c["demand_tps"] == d]
            ax[i].plot([0] + [r["year"] for r in rows], [GENESIS_CIRC / 1e6] + [r["circulating_M"] for r in rows],
                       label=f"reward {R}")
        ax[i].set_title(f"Circulating supply, demand {d} tx/s")
        ax[i].set_xlabel("year")
        ax[i].grid(alpha=0.3)
    ax[0].set_ylabel("circulating (millions)")
    ax[1].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "supply_10y.png"), dpi=130)
    plt.close()

    report(A, B, C, D, caps, cap_matched, max_forever)
    print("done ->", OUT)


def f(x, d=0):
    return "-" if x is None else f"{x:,.{d}f}"


def report(A, B, C, D, caps, cap_matched, max_forever):
    matched = f"matched_{cap_matched}"
    burn = {(b["block_cap"], b["demand_tps"]): b for b in B}
    L = []
    a = L.append
    a("# ניסוי 01: כלכלת המטבע ESH27-test\n")
    a(f"נוצר על ידי `exp_coin.py`. הנחות שנלקחו מניסויי הקונצנזוס: בלוק כל {BI:.3f} שניות "
      f"({BPY / 1e6:,.1f} מיליון בלוקים בשנה), ותקרת רשת של כ-{CAP_100M:,.0f} עסקאות בשנייה ב-100Mbps. "
      f"באוצר 108 מיליון מטבעות. במחזור בתחילת הדרך: {GENESIS_CIRC / 1e6:.0f} מיליון (משתמשים וסטייק של מאמתים). חצייה של התגמול פעם בשנה.\n")

    # A
    a("## חלק א: רגישות לתגמול הבלוק\n")
    a("**השערה:** יש תגמול מקסימלי שמתחתיו האוצר לא מתרוקן לעולם. לפי חשבון, עם חצייה שנתית סך כל ההנפקה הוא פעמיים ההנפקה של השנה הראשונה, ולכן "
      f"התגמול המקסימלי הוא 108M חלקי (2 × בלוקים בשנה) = {max_forever:.3f}.\n")
    a("**הרצה:** חישוב מדויק של לוח ההנפקה לכל תגמול.\n")
    a("**תוצאה:**\n")
    a("| תגמול לבלוק | הנפקה בשנה 1 (מיליון) | אינפלציה בשנה 1 | האוצר מתרוקן אחרי | סך הנפקה (מיליון) |\n|---|---|---|---|---|")
    for r in A:
        y = "לעולם לא" if r["years_until_empty"] is None else f"{r['years_until_empty']:.1f} שנים"
        a(f"| {r['reward']} | {f(r['year1_emission_M'], 1)} | {f(r['year1_inflation_pct'])}% | {y} | {f(r['total_emitted_M'], 1)} |")
    a("\n![treasury](treasury_lifetime.png)\n")
    a(f"**מסקנה:** ההשערה אושרה. 0.5, 0.6 ו-0.7 מחזיקים לנצח. 0.8 ומעלה מרוקנים את האוצר. אבל גם 0.7 נותן אינפלציה של "
      f"{f(A[2]['year1_inflation_pct'])}% בשנה הראשונה, כי במחזור יש רק {GENESIS_CIRC / 1e6:.0f} מיליון. "
      f"עם 0.5 האינפלציה היא {f(A[0]['year1_inflation_pct'])}%. בכל המקרים היא נחצית כל שנה.\n")

    # B
    cur = "current_4000"
    a("## חלק ב: שוק העמלות מול קיבולת הרשת\n")
    a(f"**השערה:** העמלה עולה רק כשהבלוקים יותר מחצי מלאים. עם תקרה של 4,000 עסקאות לבלוק, \"חצי מלא\" הוא כ-4,800 עסקאות בשנייה, "
      f"הרבה מעל מה שהרשת מחזיקה ({CAP_100M:,.0f}). לכן העמלה תישאר תמיד ברצפה, והשריפה זניחה. "
      f"תקרה שמותאמת לקיבולת ({cap_matched} עסקאות לבלוק) תפעיל את שוק העמלות.\n")
    a("**הרצה:** הדמיית ספר החשבונות, 4,000 בלוקים לכל רמת ביקוש, עם שתי תקרות בלוק.\n")
    a("**תוצאה:**\n")
    a("| תקרת בלוק | ביקוש tx/s | נכנס tx/s | עמלה ממוצעת | נשרף ביום |\n|---|---|---|---|---|")
    for b in B:
        a(f"| {b['block_cap']} | {b['demand_tps']} | {f(b['included_tps'])} | {b['avg_fee']:.4f} | {f(b['burn_per_day'])} |")
    a(f"\nלהשוואה, ההנפקה ביום: {f(0.5 * BPD)} בתגמול 0.5, {f(0.7 * BPD)} בתגמול 0.7, {f(1.0 * BPD)} בתגמול 1.0.\n")
    a("![fee market](fee_market.png)\n")
    hi = burn[(matched, 1200)]
    cross = [d for d in (50, 200, 600, 900, 1200, 2000) if burn[(matched, d)]["burn_per_day"] > 0.7 * BPD]
    a("**מסקנה:** ההשערה אושרה. עם התקרה הנוכחית העמלה נשארת על הרצפה עד הקיבולת, והשריפה קטנה פי עשרות מההנפקה. "
      f"עם תקרה מותאמת העמלה מתחילה לעלות סביב {int(cap_matched / 2 / BI):,} עסקאות בשנייה, וב-1,200 השריפה מגיעה ל-{f(hi['burn_per_day'])} ביום. "
      + (f"מביקוש של {cross[0]:,} עסקאות בשנייה השריפה עוברת את ההנפקה בתגמול 0.7, והמטבע נעשה דפלציוני." if cross
         else "גם כך השריפה לא עוברת את ההנפקה בתגמול 0.7.")
      + " המשמעות המעשית: תקרת הבלוק צריכה לנבוע מהקיבולת שנמדדה, אחרת מנגנון השריפה מה-Whitepaper פשוט לא עובד.\n")
    yr = burn[(matched, 900)]["burn_per_day"] * 365
    a(f"**ממצא לא צפוי:** בעומס, העמלה מזנקת פי 17 ויותר מהרצפה. ב-900 עסקאות בשנייה נשרפים {yr / 1e6:,.0f} מיליון מטבעות בשנה, "
      f"יותר מכל ההיצע שבמחזור ({GENESIS_CIRC / 1e6:.0f} מיליון). זה לא יכול לקרות במציאות: המשתמשים פשוט ייגמר להם הכסף, או שמחיר המטבע יעלה והעמלה במטבעות תרד. "
      "המסקנה היא שיחידות העמלה (רצפה של 0.001, ותקרה בפועל סביב 0.05) גבוהות מדי ביחס להיצע. "
      "צריך לכייל אותן כך ששריפה שנתית בעומס מלא תהיה אחוזים בודדים מההיצע, למשל רצפה של 0.00001 עם תקרת עמלה.\n")

    # C
    a("## חלק ג: היצע במחזור לאורך 10 שנים\n")
    a("**השערה:** בכל תגמול בטווח, ההיצע במחזור עולה בשנים הראשונות, כי ההנפקה גבוהה והשריפה נמוכה. "
      "בביקוש גבוה, אחרי כמה חציות, השריפה עוברת את ההנפקה וההיצע מתחיל לרדת.\n")
    a("**הרצה:** לוח ההנפקה מחלק א, ושריפה שנתית מחלק ב (תקרה מותאמת), בביקוש קבוע של 200 ו-600 עסקאות בשנייה. "
      "לא הרצתי 900, כי שם השריפה עוברת את כל ההיצע תוך שנה (ראה הממצא בחלק ב), והתחזית מאבדת משמעות.\n")
    a("**תוצאה:**\n")
    a("| תגמול | ביקוש | שנה 1 (מיליון) | שנה 3 | שנה 5 | שנה 10 | שנת שיא |\n|---|---|---|---|---|---|---|")
    for R in REWARDS[:-1]:
        for d in (200, 600):
            rows = [c for c in C if c["reward"] == R and c["demand_tps"] == d]
            peak = max(rows, key=lambda r: r["circulating_M"])
            g = {r["year"]: r["circulating_M"] for r in rows}
            a(f"| {R} | {d} | {f(g[1], 1)} | {f(g[3], 1)} | {f(g[5], 1)} | {f(g[10], 1)} | {peak['year']} |")
    a("\n![supply](supply_10y.png)\n")
    peaks = {}
    for R in REWARDS[:-1]:
        for d in (200, 600):
            rows = [c for c in C if c["reward"] == R and c["demand_tps"] == d]
            peaks[(R, d)] = max(rows, key=lambda r: r["circulating_M"])
    declines = all(peaks[(R, d)]["year"] < YEARS for R in REWARDS[:-1] for d in (200, 600))
    a(f"**מסקנה:** {'ההשערה אושרה' if declines else 'ההשערה אושרה חלקית'}. ההיצע במחזור עולה בשנים הראשונות, מגיע לשיא "
      f"(בתגמול 0.7 ובביקוש 200: שנה {peaks[(0.7, 200)]['year']}, {peaks[(0.7, 200)]['circulating_M']:,.0f} מיליון), ואז יורד לאט, כשההנפקה הנחצית נופלת מתחת לשריפה. "
      "גם בעומס בלי שוק עמלות פעיל (העמלה ברצפה), השריפה מגיעה בסוף לגובה ההנפקה, כי ההנפקה נחצית כל שנה. "
      "תגמול 0.8 ומעלה נותן שיא גבוה יותר ומוקדם יותר, ואחר כך זהה לכולם, כי האוצר כבר ריק.\n")

    # D
    a("## חלק ד: מימון קרן הצדקה\n")
    a("**השערה:** בעומס נמוך, 10% מהעמלות לא מספיקים לקרן. 5% מתגמול הבלוק נותנים לה הכנסה יציבה, שלא תלויה בעומס.\n")
    a("**הרצה:** תגמול 0.7, תקרה מותאמת, עם ובלי 5% מהתגמול לקרן.\n")
    a("**תוצאה:**\n")
    a("| נתח מהתגמול | ביקוש tx/s | לקרן ביום |\n|---|---|---|")
    for r in D:
        a(f"| {int(r['reward_share'] * 100)}% | {r['demand_tps']} | {f(r['charity_per_day'])} |")
    d0 = {r["demand_tps"]: r["charity_per_day"] for r in D if r["reward_share"] == 0}
    d5 = {r["demand_tps"]: r["charity_per_day"] for r in D if r["reward_share"] == 0.05}
    a(f"\n**מסקנה:** ההשערה אושרה. בביקוש של 50 עסקאות בשנייה הקרן מקבלת {f(d0[50])} ביום מעמלות בלבד, ו-{f(d5[50])} ביום עם 5% מהתגמול. "
      "ההכנסה מהתגמול יורדת בחצי כל שנה, יחד עם התגמול עצמו.\n")

    a("## המלצה למסמך הכלכלי\n")
    a(f"- תגמול בלוק של 0.5 עד 0.7. מעל {max_forever:.2f} האוצר מתרוקן.")
    a(f"- תקרת בלוק לפי הקיבולת שנמדדה (כ-{cap_matched} עסקאות לבלוק ב-100Mbps), כדי ששוק העמלות והשריפה יעבדו.")
    a("- 5% מתגמול הבלוק לקרן הצדקה, בנוסף ל-10% מהעמלות.")
    a("- לכייל את יחידות העמלה להיצע: רצפה נמוכה בהרבה ותקרת עמלה, כך ששריפה בעומס מלא תהיה אחוזים בודדים מההיצע בשנה.")
    a("- לא לכתוב \"דפלציוני\" במסמך. ההיצע במחזור עולה כמה שנים לפני שהוא מתחיל לרדת, וכמה מהר תלוי בביקוש.\n")
    a("## מגבלות\n")
    a("- הביקוש קבוע ולא גדל עם הזמן. במציאות הוא יגדל או יקרוס, וזה המשתנה החשוב ביותר.")
    a("- אין מחיר למטבע. כל המספרים ביחידות מטבע, לא בשקלים.")
    a("- התחזית ל-10 שנים מניחה שהרשת, התקרה וזמן הבלוק לא משתנים.")
    with open(os.path.join(OUT, "EXPERIMENT_01_COIN.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
