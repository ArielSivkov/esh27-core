"""
ניסוי 1 · מחיר השבריר-שנייה
================================
כמה שווה לראות פוסט שמזיז שוק Δ מילישניות לפני כולם, ואיזה מנגנון שוק מאפס את היתרון?

הכל מקומי ומדומה: אין חיבור לשום API, ארנק או בורסה. כל הפרמטרים הם הנחות, והם מרוכזים ב-BASE.

מודל:
- פוסטים מגיעים כמה פעמים ביום. חלק קטן מהם מזיז את מחיר הטוקן ביחס r (קפיצה בלוג-נורמלי).
- הטוקן נסחר בבריכת AMM של מכפלה קבועה (x*y=k), שבה Y דולר בצד הדולרי.
  מי שמזיז ראשון את הבריכה למחיר החדש מרוויח Y*(sqrt(r')-1)^2, כאשר r' הוא הקפיצה אחרי עמלת הבריכה.
  זה ההפסד של ספקי הנזילות (LVR), והוא בדיוק מה שהמנוי קונה.
- המנוי רואה את הפוסט ב-t=0. המתחרים רואים אותו ב-t=Δ.
  כל אחד צריך גם לנתח את הפוסט עם מודל שפה (זמן הסקה) ולשלוח את העסקה (רשת).
- זירות:
    continuous : בורסה רציפה, מי שמגיע ראשון זוכה.
    solana     : בלוק כל 400ms. בתוך בלוק עם יותר ממשתתף אחד יש מכרז עדיפות, ו-90% מהרווח הולך לוולידטור.
    ethereum   : בלוק כל 12 שניות, אותו כלל.
    fba        : מכירה פומבית במנות (Frequent Batch Auction) בחלון W. כל מי שנכנס לאותה מנה
                 מתחלק ברווח שווה בשווה, ואין מכרז עדיפות.
- ניסוי נגדי: בריכה שמנויה בעצמה לאותו פיד, ומעלה עמלה ל-surge_fee לכמה שניות מיד עם פרסום הפוסט.
"""
import json
import numpy as np

BASE = dict(
    posts_per_day=18, p_relevant=0.08, days=30,
    jump_median=0.04, jump_sigma=0.9, jump_cap=0.6,   # |ln r|
    pool_usd=3_000_000, pool_fee=0.003,
    n_competitors=25,
    llm_ms_median=600, llm_sigma=0.5,                 # זמן הסקה של מודל שפה לסיווג הפוסט
    net_ms_median=40, net_sigma=0.6,
    subscriber_llm_ms=250,                            # המנוי משתמש במודל קטן ומהיר
    priority_take=0.9,
    api_cost=100_000,
    months=400,
)
VENUES = {"continuous": 0.0, "solana": 400.0, "ethereum": 12_000.0}


def arb_profit(Y, ln_r, fee):
    eff = np.maximum(np.abs(ln_r) - np.log1p(fee), 0.0)
    return Y * (np.exp(eff / 2) - 1.0) ** 2


def draw_month(rng, p):
    n_posts = rng.poisson(p["posts_per_day"] * p["days"])
    n_rel = rng.binomial(n_posts, p["p_relevant"])
    ln_r = np.minimum(rng.lognormal(np.log(p["jump_median"]), p["jump_sigma"], n_rel), p["jump_cap"])
    ln_r *= rng.choice([-1, 1], n_rel)
    return ln_r


def race_share(rng, p, delta, venue, n, block_ms=None, fba_ms=None):
    """חלק הרווח שהמנוי לוקח מכל פוסט. מחזיר מערך באורך n."""
    sub = p["subscriber_llm_ms"] + rng.lognormal(np.log(p["net_ms_median"]), p["net_sigma"], n)
    k = p["n_competitors"]
    comp = (delta
            + rng.lognormal(np.log(p["llm_ms_median"]), p["llm_sigma"], (n, k))
            + rng.lognormal(np.log(p["net_ms_median"]), p["net_sigma"], (n, k)))
    if venue == "continuous":
        return (sub < comp.min(axis=1)).astype(float)
    W = fba_ms if venue == "fba" else block_ms
    phase = rng.uniform(0, W, n)                       # תזמון הבלוק או המנה ביחס לפוסט
    s_sub = np.ceil((sub - phase) / W)                 # מספר הבלוק או המנה שהעסקה נכנסת אליהם
    s_comp = np.ceil((comp - phase[:, None]) / W)
    first_comp = s_comp.min(axis=1)
    alone = s_sub < first_comp
    same = s_sub == first_comp
    if venue == "fba":
        m = (s_comp == s_sub[:, None]).sum(axis=1)
        return np.where(alone, 1.0, np.where(same, 1.0 / (m + 1), 0.0))
    # בלוקים: בתוך בלוק עם מתחרים, מכרז העדיפות מעביר את רוב הרווח לוולידטור. המנוי זוכה ב-1/(m+1) מהמקרים.
    m = (s_comp == s_sub[:, None]).sum(axis=1)
    return np.where(alone, 1.0, np.where(same, (1 - p["priority_take"]) / (m + 1), 0.0))


def monthly_value(p, delta, venue, fee=None, seed=0, fba_ms=None, surge=None):
    rng = np.random.default_rng(seed)
    out_sub, out_lp = [], []
    for _ in range(p["months"]):
        ln_r = draw_month(rng, p)
        n = len(ln_r)
        if n == 0:
            out_sub.append(0.0); out_lp.append(0.0); continue
        f_sub = fee if fee is not None else p["pool_fee"]
        prof = arb_profit(p["pool_usd"], ln_r, f_sub)
        if venue == "fba":
            share = race_share(rng, p, delta, "fba", n, fba_ms=fba_ms)
        else:
            share = race_share(rng, p, delta, venue, n, block_ms=VENUES[venue])
        if surge is not None:
            # הבריכה מנויה בעצמה: היא מעלה עמלה מ-t=0 ולמשך surge["window_ms"].
            # המנוי צריך לעבור עמלה גבוהה בעצמו, כי גם הוא מגיע אחרי t=0.
            prof = arb_profit(p["pool_usd"], ln_r, surge["fee"])
            # אחרי שהחלון נסגר, מישהו סוגר את הפער שנשאר בעמלה הרגילה. גם זה הפסד של ספקי הנזילות.
            gap = np.sign(ln_r) * np.minimum(np.abs(ln_r), np.log1p(surge["fee"]))
            lp = prof + arb_profit(p["pool_usd"], gap, p["pool_fee"])
            # העמלה הגבוהה שהמנוי משלם נכנסת לספקי הנזילות: עמלה כפול נפח העסקה בדולרים.
            eff = np.maximum(np.abs(ln_r) - np.log1p(surge["fee"]), 0.0)
            lp = lp - surge["fee"] * p["pool_usd"] * np.abs(np.exp(eff / 2) - 1.0)
        else:
            lp = prof
        out_sub.append(float((prof * share).sum()))
        out_lp.append(float(lp.sum()))
    a = np.array(out_sub)
    return dict(mean=a.mean(), p10=np.percentile(a, 10), p50=np.median(a), p90=np.percentile(a, 90),
                p_breakeven=float((a >= p["api_cost"]).mean()), lp_loss=float(np.mean(out_lp)))


def run():
    p = dict(BASE)
    res = {"params": p}

    deltas = [0, 50, 100, 200, 300, 500, 800, 1200, 2000, 4000]
    res["A_lead_by_venue"] = {
        v: [{"delta_ms": d, **monthly_value(p, d, v, seed=1)} for d in deltas] for v in VENUES
    }

    pools = [500_000, 1_000_000, 3_000_000, 10_000_000, 30_000_000]
    res["A2_pool_size_at_500ms_solana"] = [
        {"pool_usd": Y, **monthly_value({**p, "pool_usd": Y}, 500, "solana", seed=2)} for Y in pools
    ]

    windows = [100, 250, 500, 1000, 2000, 5000]
    res["B_fba_at_500ms"] = [{"window_ms": w, **monthly_value(p, 500, "fba", seed=3, fba_ms=w)} for w in windows]

    res["C_surge_fee_solana_500ms"] = [
        {"surge_fee": f, **monthly_value(p, 500, "solana", seed=4, surge={"fee": f, "window_ms": 3000})}
        for f in [0.003, 0.01, 0.02, 0.05, 0.10]
    ]

    llm = [100, 300, 600, 1200, 2400]
    res["D_competitor_llm_latency_continuous_200ms"] = [
        {"llm_ms_median": L, **monthly_value({**p, "llm_ms_median": L}, 200, "continuous", seed=5)} for L in llm
    ]
    return res


if __name__ == "__main__":
    r = run()
    with open("results.json", "w") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    fm = lambda x: f"${x:,.0f}"
    print("A · שווי חודשי למנוי לפי יתרון זמן (ממוצע | חציון | סיכוי לכסות $100k)")
    for v, rows in r["A_lead_by_venue"].items():
        print(" ", v)
        for x in rows:
            print(f"    Δ={x['delta_ms']:>5}ms  {fm(x['mean']):>12} | {fm(x['p50']):>12} | {x['p_breakeven']:.0%}")
    print("  הפסד חודשי ממוצע של ספקי הנזילות (LVR מכל המקורות):", fm(r["A_lead_by_venue"]["solana"][0]["lp_loss"]))
    print("A2 · גודל בריכה, Solana, Δ=500ms")
    for x in r["A2_pool_size_at_500ms_solana"]:
        print(f"    Y={fm(x['pool_usd']):>12}  {fm(x['mean']):>12} | {x['p_breakeven']:.0%}")
    print("B · מכירה פומבית במנות, Δ=500ms")
    for x in r["B_fba_at_500ms"]:
        print(f"    W={x['window_ms']:>5}ms  {fm(x['mean']):>12} | {x['p_breakeven']:.0%}")
    print("C · עמלת חירום בבריכה שמנויה לפיד, Solana, Δ=500ms")
    for x in r["C_surge_fee_solana_500ms"]:
        print(f"    fee={x['surge_fee']:.1%}  מנוי {fm(x['mean']):>12} | הפסד LP נטו {fm(x['lp_loss']):>12}")
    print("D · זמן הסקה של המתחרים, בורסה רציפה, Δ=200ms")
    for x in r["D_competitor_llm_latency_continuous_200ms"]:
        print(f"    LLM={x['llm_ms_median']:>5}ms  {fm(x['mean']):>12} | {x['p_breakeven']:.0%}")
