"""הדמיית טוקנומיקס v0 — "קרדיט עיר" (CRD) בתוך אשדוד הווירטואלית.

הדמיה בלבד. אין כאן שום חיבור לרשת, ארנק או כסף.
הרצה:  python3 tokenomics_sim.py   (פלט: results.md לצד הקובץ)

מודל:
- סוכנים מרוויחים CRD על עבודה (בנייה, יצירה, שירות) מתוך "ברז" הנפקה יומי שדועך.
- סוכנים מוציאים CRD על מחשוב / בנייה / גישה; אחוז מכל הוצאה נשרף (sink), השאר לאוצר העיר.
- תקרת היצע קשיחה. בודקים: אינפלציה, ריכוזיות (Gini, top-10%), וניצול (חוות sybil).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

MAX_SUPPLY = 1_000_000_000
DAYS = 730


@dataclass
class Params:
    name: str
    n_agents: int = 500
    daily_emission: float = 400_000      # CRD ביום בהתחלה
    emission_decay: float = 0.998        # דעיכה יומית (~ חצי בשנה)
    burn_rate: float = 0.30              # חלק מכל הוצאה שנשרף
    spend_fraction: float = 0.25         # כמה מהיתרה סוכן מוציא ביום (אם יש לו מה לעשות)
    per_agent_daily_cap: float = 5_000   # תקרת הרוויח יומית לסוכן (אנטי-ניצול)
    sybil_agents: int = 0                # סוכנים מזויפים של תוקף אחד
    sybil_skill: float = 1.0             # כמה "עבודה" כל sybil מצליח לזייף
    proof_of_work_filter: bool = True    # האם יש סינון איכות לעבודה (מקטין sybil)
    treasury_recycle: float = 0.01      # חלק מאוצר העיר שחוזר כתגמולים כל יום
    seed: int = 27


@dataclass
class Agent:
    skill: float
    balance: float = 0.0
    earned: float = 0.0
    sybil: bool = False


@dataclass
class Result:
    p: Params
    supply: list = field(default_factory=list)
    burned: float = 0.0
    treasury: float = 0.0


def gini(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    s = sum(xs)
    if s == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * cum) / (n * s) - (n + 1) / n


def run(p: Params) -> Result:
    rng = random.Random(p.seed)
    agents = [Agent(skill=rng.lognormvariate(0, 0.6)) for _ in range(p.n_agents)]
    for _ in range(p.sybil_agents):
        skill = p.sybil_skill * (0.15 if p.proof_of_work_filter else 1.0)
        agents.append(Agent(skill=skill, sybil=True))

    r = Result(p)
    minted = 0.0
    emission = p.daily_emission
    for _day in range(DAYS):
        # 1) הנפקה: מחולקת לפי עבודה (skill * רעש), עם תקרה לסוכן
        room = max(0.0, MAX_SUPPLY - minted)
        new_mint = min(emission, room)
        recycled = r.treasury * p.treasury_recycle
        r.treasury -= recycled
        today = new_mint + recycled
        work = [a.skill * rng.uniform(0.5, 1.5) for a in agents]
        total_work = sum(work) or 1.0
        for a, w in zip(agents, work):
            pay = min(today * w / total_work, p.per_agent_daily_cap)
            a.balance += pay
            a.earned += pay
        minted += new_mint  # עודף מעל התקרה לסוכן פשוט לא מונפק/לא מחולק (פישוט)
        emission *= p.emission_decay

        # 2) הוצאה: sink. sybil-ים לא מוציאים (הם חוות) — זה בדיוק הסיכון
        for a in agents:
            if a.sybil:
                continue
            spend = a.balance * p.spend_fraction * rng.uniform(0.5, 1.0)
            a.balance -= spend
            r.burned += spend * p.burn_rate
            r.treasury += spend * (1 - p.burn_rate)

        circ = sum(a.balance for a in agents)
        r.supply.append(circ)
    r.minted = minted
    r.agents = agents
    return r


def summarize(r: Result) -> dict:
    bal = [a.balance for a in r.agents]
    bal_sorted = sorted(bal, reverse=True)
    top10 = sum(bal_sorted[: max(1, len(bal) // 10)]) / (sum(bal) or 1)
    earned = sum(a.earned for a in r.agents) or 1
    syb = sum(a.earned for a in r.agents if a.sybil) / earned
    s = r.supply
    infl_y1 = (s[364] - s[0]) / (s[0] or 1)
    infl_y2 = (s[729] - s[364]) / (s[364] or 1)
    return {
        "minted_pct_of_cap": r.minted / MAX_SUPPLY,
        "circulating_end": s[-1],
        "burned": r.burned,
        "treasury": r.treasury,
        "growth_y1": infl_y1,
        "growth_y2": infl_y2,
        "gini": gini(bal),
        "top10_share": top10,
        "sybil_share": syb,
    }


SCENARIOS = [
    Params("בסיס"),
    Params("בלי שריפה", burn_rate=0.0),
    Params("בלי הוצאה (אין מה לקנות)", spend_fraction=0.01),
    Params("תקיפת sybil, עם סינון", sybil_agents=500),
    Params("תקיפת sybil, בלי סינון ובלי תקרה", sybil_agents=500,
           proof_of_work_filter=False, per_agent_daily_cap=1e12),
    Params("הנפקה אגרסיבית", daily_emission=2_000_000, emission_decay=0.9995),
]


def main() -> None:
    rows = []
    for p in SCENARIOS:
        rows.append((p.name, summarize(run(p))))
    out = [
        "# תוצאות הדמיית טוקנומיקס v0 (CRD)",
        "",
        "> הדמיה בלבד, מודל פשוט. מספרים להשוואה בין תרחישים, לא תחזית.",
        "",
        "| תרחיש | % מהתקרה שהונפק | בידי סוכנים בסוף | באוצר העיר | נשרף | שינוי במחזור, שנה 2 | Gini | 10% העליונים | התוקף קיבל מהתגמולים |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, m in rows:
        out.append(
            f"| {name} | {m['minted_pct_of_cap']:.1%} | {m['circulating_end']:,.0f} | "
            f"{m['treasury']:,.0f} | {m['burned']:,.0f} | {m['growth_y2']:+.0%} | {m['gini']:.2f} | "
            f"{m['top10_share']:.0%} | {m['sybil_share']:.0%} |"
        )
    path = Path(__file__).with_name("results.md")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
