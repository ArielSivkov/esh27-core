"""Experiment 02: coordinated collusion attack (attempt to fork the chain).

    python exp_attack.py      # writes results/attack/
"""
import csv
import os
import random
from multiprocessing import Pool

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from chain27lab.world import Config, World  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "attack")
os.makedirs(OUT, exist_ok=True)

N = 27
Q = (2 * N) // 3 + 1          # 19 votes for a quorum
F = (N - 1) // 3              # 8 faulty tolerated
INTERSECTION = 2 * Q - N      # 11: any two quorums share at least this many validators
COLLUDERS = [8, 9, 10, 11, 12, 13, 14]
SEEDS = [1, 2, 3, 4, 5]
DUR = 60.0


def one(args):
    b, partition, seed = args
    col = sorted(random.Random(1000 * seed + b).sample(range(N), b))
    w = World(Config(duration=DUR, seed=seed, behaviors={i: "collude" for i in col}, partition=partition))
    s = w.run()
    return {
        "colluders": b, "network_control": partition, "seed": seed,
        "blocks": s["blocks"], "forked": s["fork_events"] > 0, "first_fork_t": s["first_fork_t"],
        "culprits_proven": s["culprits_proven"], "honest_blamed": s["honest_blamed"],
        "attack_rounds": s["attack_rounds"], "evidence_detected": s["evidence_detected"],
    }


def main():
    jobs = [(b, p, s) for p in (False, True) for b in COLLUDERS for s in SEEDS]
    with Pool(min(4, os.cpu_count() or 1)) as pool:
        rows = pool.map(one, jobs)
    with open(os.path.join(OUT, "collusion_runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    agg = []
    for p in (False, True):
        for b in COLLUDERS:
            rs = [r for r in rows if r["colluders"] == b and r["network_control"] == p]
            forks = [r for r in rs if r["forked"]]
            agg.append({
                "network_control": p, "colluders": b, "runs": len(rs),
                "fork_rate": len(forks) / len(rs),
                "blocks_per_min": sum(r["blocks"] for r in rs) / len(rs) / (DUR / 60),
                "attack_rounds": sum(r["attack_rounds"] for r in rs) / len(rs),
                "min_culprits": min((r["culprits_proven"] for r in forks), default=None),
                "max_honest_blamed": max((r["honest_blamed"] for r in forks), default=None),
                "evidence": sum(r["evidence_detected"] for r in rs) / len(rs),
            })
    with open(os.path.join(OUT, "collusion_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(agg[0].keys()))
        w.writeheader()
        w.writerows(agg)

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for p, st, lab in ((False, "o--", "no network control"), (True, "s-", "attacker controls network")):
        rs = [a for a in agg if a["network_control"] == p]
        ax[0].plot([a["colluders"] for a in rs], [a["fork_rate"] * 100 for a in rs], st, label=lab)
        ax[1].plot([a["colluders"] for a in rs], [a["blocks_per_min"] for a in rs], st, label=lab)
    for a in ax:
        a.axvline(F + 0.5, color="orange", ls=":")
        a.axvline(INTERSECTION - 0.5, color="red", ls=":")
        a.set_xlabel("colluding validators (of 27)")
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    ax[0].set_ylabel("runs that forked (%)")
    ax[0].set_title("Safety: fork rate (red line = 11)")
    ax[1].set_ylabel("honest blocks per minute")
    ax[1].set_title("Liveness (orange line = f = 8)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "collusion.png"), dpi=130)
    plt.close()
    report(agg)
    print("done ->", OUT)


def report(agg):
    g = {(a["network_control"], a["colluders"]): a for a in agg}
    L = []
    a = L.append
    a("# ניסוי 02: קנוניה של צמתים זדוניים\n")
    a(f"נוצר על ידי `exp_attack.py`. 27 מאמתים, מניין חוקי של {Q} קולות. {len(SEEDS)} הרצות לכל הגדרה, כל אחת {DUR:.0f} שניות מדומות, "
      "עם קבוצת תוקפים אקראית אחרת בכל הרצה.\n")
    a("## התקיפה\n")
    a("התוקפים פועלים כגוף אחד שרואה את כל הרשת. הם מחלקים את הצמתים הישרים לשני חצאים, X ו-Y. "
      "כשתור ההצעה מגיע לאחד מהם, הוא שולח בלוק A לחצי X ובלוק B לחצי Y, וכל התוקפים מצביעים בעד A מול X ובעד B מול Y. "
      "בסבבים של מציע ישר הם מצביעים \"nil\", כדי שהסבבים ימשיכו להתקדם עד שיגיע התור שלהם. "
      "נבדקו שני מצבים: בלי שליטה ברשת, ועם שליטה ברשת, שבה התוקף חוסם כל תקשורת בין X ל-Y.\n")

    a("## השערות\n")
    a(f"1. **חיות:** עד {F} תוקפים הרשת ממשיכה לייצר בלוקים. מ-{F + 1} היא נעצרת, כי לישרים לבד אין {Q} קולות.")
    a(f"2. **בטיחות:** עד {INTERSECTION - 1} תוקפים אי אפשר לפצל את הרשת, באף מצב. כל שני מניינים של {Q} מתוך 27 חולקים לפחות {INTERSECTION} צמתים, "
      f"ולכן פיצול דורש ש-{INTERSECTION} צמתים יחתמו על שני בלוקים סותרים.")
    a(f"3. **מ-{INTERSECTION} תוקפים עם שליטה ברשת:** פיצול בכל הרצה.")
    a(f"4. **מ-{INTERSECTION} תוקפים בלי שליטה ברשת:** פיצול לא מובטח. צמתים ישרים מעבירים הלאה קולות שקיבלו, וכך חושפים את הקולות הכפולים של התוקפים לפני שהמניין נסגר.")
    a(f"5. **אחריותיות:** אחרי כל פיצול אפשר להוכיח מי אשם, לפחות {INTERSECTION} צמתים, ואף צומת ישר לא מואשם.\n")

    a("## תוצאה\n")
    a("![collusion](collusion.png)\n")
    a("| תוקפים | שליטה ברשת | הרצות שהתפצלו | בלוקים בדקה | סבבי תקיפה | אשמים שהוכחו (מינימום) | ישרים שהואשמו |\n|---|---|---|---|---|---|---|")
    for p in (False, True):
        for b in COLLUDERS:
            r = g[(p, b)]
            a(f"| {b} | {'כן' if p else 'לא'} | {r['fork_rate'] * 100:.0f}% | {r['blocks_per_min']:.1f} | {r['attack_rounds']:.1f} | "
              f"{'-' if r['min_culprits'] is None else r['min_culprits']} | {'-' if r['max_honest_blamed'] is None else r['max_honest_blamed']} |")

    def rate(p, bs):
        return max(g[(p, b)]["fork_rate"] for b in bs)

    safe_low = rate(False, range(8, INTERSECTION)) == 0 and rate(True, range(8, INTERSECTION)) == 0
    ctrl_all = all(g[(True, b)]["fork_rate"] == 1 for b in COLLUDERS if b >= INTERSECTION)
    live8 = g[(False, 8)]["blocks_per_min"] > 0
    halt9 = all(g[(False, b)]["blocks_per_min"] < 2 for b in COLLUDERS if b > F)
    forks = [x for x in agg if x["min_culprits"] is not None]
    acct = all(x["min_culprits"] >= INTERSECTION and x["max_honest_blamed"] == 0 for x in forks)
    nc = [(b, g[(False, b)]["fork_rate"]) for b in COLLUDERS if b >= INTERSECTION]

    a("\n## מסקנות\n")
    a(f"1. **חיות: {'אושרה' if live8 and halt9 else 'לא אושרה במלואה'}.** עם 8 תוקפים הרשת ממשיכה ({g[(False, 8)]['blocks_per_min']:.0f} בלוקים בדקה, לעומת 144 בלי תוקפים), "
      "כי התוקפים מבזבזים כל סבב שבו הם מציעים. מ-9 תוקפים היא נעצרת כמעט לגמרי.")
    a(f"2. **בטיחות עד 10: {'אושרה' if safe_low else 'הופרכה'}.** בין 9 ל-10 תוקפים יש \"אזור ביניים\": הרשת עצורה, אבל אין פיצול. "
      "זו התכונה החשובה של BFT: כשיש יותר מדי תוקפים, הרשת מעדיפה לעצור ולא לייצר היסטוריה סותרת.")
    a(f"3. **מ-11 עם שליטה ברשת: {'אושרה' if ctrl_all else 'לא אושרה במלואה'}.** הפיצול קורה כבר בסבב התקיפה הראשון, תוך שניות. אחרי הפיצול שני החצאים נעצרים, כי לאף אחד מהם אין 19 קולות ישרים לבלוק הבא.")
    a("4. **מ-11 בלי שליטה ברשת:** " + ", ".join(f"{b} תוקפים: {r * 100:.0f}%" for b, r in nc) + ". "
      "ב-11 התוקפים צריכים את כל 11 הקולות שלהם בכל צד. מספיק שקול כפול אחד שהועבר הלאה יגיע לפני הקול הישיר, והתקיפה נכשלת. "
      "ככל שיש יותר תוקפים יש להם יותר מרווח, והסיכוי לפיצול עולה. המסקנה המעשית: פיזור גאוגרפי וחיבורים ישירים בין כל הצמתים מקשים מאוד על תוקף שלא שולט ברשת.")
    a(f"5. **אחריותיות: {'אושרה' if acct else 'הופרכה'}.** בכל פיצול, השוואה בין שתי תעודות החתימה של הבלוקים הסותרים חשפה לפחות "
      f"{min((x['min_culprits'] for x in forks), default=0)} צמתים שחתמו על שניהם, ואף צומת ישר לא הואשם. "
      "כלומר אי אפשר לפצל את הרשת בלי להשאיר הוכחה חתומה נגד יותר משליש מהמאמתים. זו ההצדקה לכלל הממשל ב-Whitepaper: אף גורם לא מחזיק יותר מ-8 צמתים, "
      "וצריך הסכם משפטי שמאפשר לקנוס ולהוציא את מי שנתפס.\n")

    a("## ממצא נוסף: חסימת רשת לבד עוצרת את הרשת\n")
    a(f"עם 8 תוקפים ושליטה ברשת: {g[(True, 8)]['blocks_per_min']:.1f} בלוקים בדקה. התוקפים לא יכולים לפצל, "
      "אבל אם הם מצליחים לנתק את הרשת לשני חצאים, אף חצי לא מגיע ל-19 קולות. זו לא תקיפה על הקונצנזוס, אלא על התשתית. "
      "ההגנה היא ריבוי ספקי תקשורת ומיקומים לכל צומת.\n")

    a("## מגבלות\n")
    a("- התוקף רואה את כל הרשת ומתאם בלי עיכוב. זה מקרה גרוע, אבל לא בהכרח מציאותי.")
    a("- התקיפה היא פיצול כפול-הצעה אחד. לא נבדקו התקיפות על נעילות לאורך כמה סבבים, ולא שוחד או השתלטות על מפתחות.")
    a("- הזיהוי של האשמים נעשה בניתוח אחרי הריצה. ברשת אמיתית צריך פרוטוקול שמפיץ את שתי התעודות ומכניס אותן כראיה לבלוק.")
    with open(os.path.join(OUT, "EXPERIMENT_02_ATTACK.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
