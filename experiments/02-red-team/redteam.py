"""
ניסוי 2 · צוות אדום אוטומטי
================================
סוכן חיפוש (אלגוריתם אבולוציוני) מחפש אסטרטגיות שמנצלות את שני המנגנונים מהניסויים הקודמים:
  חלק א: עקומת החרטה (ניסוי 0)
  חלק ב: עמלת החדשות (ניסוי 1)
אחרי כל פרצה בודקים הגנה, והסוכן מחפש שוב מול ההגנה.

הסוכן כאן הוא אופטימייזר ולא מודל שפה. בניסוי עם LLM אמיתי היה צריך מפתח API, וזה מחוץ לגבולות שאושרו.
הכל מקומי ומדומה.
"""
import json, math, random, sys
import numpy as np

P0, C, T = 0.02, 1000.0, 360

# ---------------------------------------------------------------- simulation
def simulate(seed, n_retail=300, hype=1.0, attack=None):
    R = random.Random(seed)
    s = 0.0
    price = lambda: P0 * math.exp(s / C)
    def value_of(q):          # כמה SOL יתקבלו ממכירת q טוקנים עכשיו
        return P0 * C * (math.exp(s / C) - math.exp((s - q) / C))

    wallets = []              # כל ארנק: owner, kind, cost, proceeds, entryT, exitT, tokens
    def new_wallet(owner, kind, **kw):
        w = dict(owner=owner, kind=kind, cost=0.0, proceeds=0.0, tokens=0.0, entryT=None, exitT=None,
                 entered=False, held=False, gone=False, **kw)
        wallets.append(w); return w
    def buy(w, A, t):
        nonlocal s
        ns = C * math.log(math.exp(s / C) + A / (P0 * C))
        w['tokens'] = ns - s; s = ns
        w['cost'] = A; w['entryP'] = A / w['tokens']; w['peak'] = price()
        w['entered'] = w['held'] = True; w['entryT'] = t
    def sell(w, t):
        nonlocal s
        q = w['tokens']; w['proceeds'] = value_of(q); s = max(0.0, s - q)
        w['tokens'] = 0.0; w['held'] = False; w['exitT'] = t

    for i in range(5):
        new_wallet(f'sn{i}', 'sniper', budget=3 + R.random() * 4, enterT=int(R.random() * 3), tp=2 + R.random() * 3)
    for i in range(8):
        new_wallet(f'wh{i}', 'whale', budget=8 + R.random() * 17, enterT=3 + int(R.random() * 40), tp=1.8 + R.random() * 1.7)
    for i in range(n_retail):
        new_wallet(f'rt{i}', 'retail', budget=min(20, max(0.1, math.exp(0.9 * R.gauss(0, 1)))),
                   tp=1.5 + 1.5 * math.exp(0.8 * R.gauss(0, 1)), sl=0.3 + R.random() * 0.4, panic=0.25 + R.random() * 0.25)

    # ---- attacker wallets: they act deterministically by their schedule
    A = attack or {}
    sched = {}                # t -> list of actions
    def at(t, fn): sched.setdefault(int(t), []).append(fn)
    if A.get('type') in ('sniper', 'transfer'):
        a = new_wallet('ATK', 'attacker')
        at(0, lambda t: buy(a, A['budget'], t))
        if A['type'] == 'sniper':
            at(A['sell_t'], lambda t: sell(a, t))
        else:
            b = new_wallet('ATK', 'attacker')
            def transfer(t):
                # העברה לארנק חדש. rule=reset: מחיר העלות של הארנק החדש = שווי השוק ברגע ההעברה.
                # rule=carry: מחיר העלות וזמן הכניסה עוברים עם הטוקנים.
                b['tokens'] = a['tokens']; b['held'] = b['entered'] = True
                if A['rule'] == 'reset':
                    b['cost'] = value_of(a['tokens']); b['entryT'] = t
                else:
                    b['cost'] = a['cost']; b['entryT'] = a['entryT']
                a['tokens'] = 0.0; a['held'] = False; a['gone'] = True      # הארנק הישן לא נספר
            at(A['transfer_t'], transfer)
            at(A['transfer_t'] + A['sell_gap'], lambda t: sell(b, t))
    if A.get('type') == 'wash':
        a = new_wallet('ATK', 'attacker'); b = new_wallet('ATK', 'attacker')
        tA = A['tA']
        at(tA, lambda t: buy(a, A['bA'], t))
        at(tA + A['d'] + A['e'], lambda t: sell(a, t))
        if A['bB'] > 0:       # bB=0 היא ריצת ביקורת: אותו תוקף בלי הארנק המפסיד
            at(tA + A['d'], lambda t: buy(b, A['bB'], t))
            at(tA + A['d'] + A['e'] + A['g'], lambda t: sell(b, t))

    hist = []
    honest = [w for w in wallets if w['kind'] != 'attacker']
    for t in range(T):
        p = price(); hist.append(p)
        for fn in sched.get(t, []): fn(t)
        m = p / hist[t - 8] - 1 if t >= 8 else 0.0
        hy = hype * math.exp(-t / 120)
        actors = []
        for w in honest:
            if not w['entered']:
                k = w['kind']
                if k == 'sniper' and t >= w['enterT']: actors.append(w)
                elif k == 'whale' and t >= w['enterT'] and m > -0.1: actors.append(w)
                elif k == 'retail' and R.random() < hy * (0.004 + 0.06 * max(0.0, m)): actors.append(w)
            elif w['held']: actors.append(w)
        R.shuffle(actors)
        for w in actors:
            if not w['entered']:
                buy(w, w['budget'], t); continue
            cp = price(); w['peak'] = max(w['peak'], cp); ret = cp / w['entryP']
            k = w['kind']
            if k == 'sniper': out = ret >= w['tp'] or t - w['entryT'] > 50 or ret < 0.8
            elif k == 'whale': out = ret >= w['tp'] or cp < w['peak'] * 0.6
            else: out = ret >= w['tp'] or ret <= 1 - w['sl'] or (cp < w['peak'] * (1 - w['panic']) and R.random() < 0.3) or R.random() < 0.003
            if out: sell(w, t)
    rest = [w for w in wallets if w['held']]
    R.shuffle(rest)
    for w in rest: sell(w, T)
    return [w for w in wallets if w['entered'] and not w['gone']]


# ---------------------------------------------------------------- settlement
DEFAULT_MECH = dict(fair=True, k=0.15, flip=2.0, cap=1.0, floor=0.0, rebate_min_hold=0)

def settle(wallets, mech):
    rows = []
    for w in wallets:
        profit = w['proceeds'] - w['cost']; tax = 0.0
        hold = w['exitT'] - w['entryT']
        if mech['fair'] and profit > 0:
            mult = w['proceeds'] / w['cost']
            rate = min(0.9, mech['k'] * math.log2(mult) * (1 + mech['flip'] * math.exp(-hold / 30)))
            tax = profit * max(rate, mech['floor'])
        rows.append(dict(owner=w['owner'], kind=w['kind'], cost=w['cost'], profit=profit, tax=tax, rebate=0.0, hold=hold))
    pool = sum(r['tax'] for r in rows)
    if mech['fair']:
        claim = [r for r in rows if r['profit'] < 0 and r['hold'] >= mech['rebate_min_hold']]
        for _ in range(30):
            act = [r for r in claim if r['rebate'] < mech['cap'] * -r['profit'] - 1e-12]
            if not act or pool <= 1e-12: break
            W = sum(math.sqrt(-r['profit']) for r in act); used = 0.0
            for r in act:
                g = min(pool * math.sqrt(-r['profit']) / W, mech['cap'] * -r['profit'] - r['rebate'])
                r['rebate'] += g; used += g
            pool -= used
    for r in rows: r['net'] = r['profit'] - r['tax'] + r['rebate']
    return rows

def summarize(rows):
    ret = [r for r in rows if r['kind'] == 'retail']
    atk = [r for r in rows if r['owner'] == 'ATK']
    return dict(
        retail_lose=sum(r['net'] < -1e-6 * r['cost'] for r in ret) / max(1, len(ret)),
        atk_net=sum(r['net'] for r in atk),
        atk_rebate=sum(r['rebate'] for r in atk),
        retail_rebate=sum(r['rebate'] for r in ret),
        retail_net=sum(r['net'] for r in ret),
        retail_median_roi=float(np.median([r['net'] / r['cost'] for r in ret])) if ret else 0.0,
    )

def evaluate(attack, mech, seeds):
    out = [summarize(settle(simulate(sd, attack=attack), mech)) for sd in seeds]
    return {k: float(np.mean([o[k] for o in out])) for k in out[0]}


# ---------------------------------------------------------------- search agent
def evolve(space, make_attack, mech, seeds, pop=24, gens=6, rng_seed=0):
    """אלגוריתם אבולוציוני פשוט: דוגמים, שומרים את הרבע העליון, ומשנים סביבו. המטרה: רווח נטו של התוקף."""
    rng = random.Random(rng_seed)
    def sample():
        return {k: (rng.randint(*v) if isinstance(v[0], int) else rng.uniform(*v)) for k, v in space.items()}
    def mutate(x):
        y = dict(x)
        for k, v in space.items():
            if rng.random() < 0.5:
                lo, hi = v
                if isinstance(lo, int): y[k] = min(hi, max(lo, x[k] + rng.randint(-max(1, (hi - lo) // 10), max(1, (hi - lo) // 10))))
                else: y[k] = min(hi, max(lo, x[k] + rng.gauss(0, (hi - lo) / 10)))
        return y
    popl = [sample() for _ in range(pop)]
    best = None
    for g in range(gens):
        scored = []
        for x in popl:
            sc = evaluate(make_attack(x), mech, seeds)['atk_net']
            scored.append((sc, x))
        scored.sort(key=lambda z: -z[0])
        if best is None or scored[0][0] > best[0]: best = scored[0]
        elite = [x for _, x in scored[: max(2, pop // 4)]]
        popl = elite + [mutate(rng.choice(elite)) for _ in range(pop - len(elite))]
    return best


# ---------------------------------------------------------------- part B: news fee with strategic waiting
def news_fee_game(n_comp_list, surge=0.05, base=0.003, months=300, seed=7):
    """
    בכל פוסט, N+1 מבצעי ארביטראז' בוחרים: לסחור בתוך חלון העמלה הגבוהה, או לחכות לסופו ולהתחרות בעמלה הרגילה.
    שיווי משקל סימטרי: סוחרים בחלון אם הפרס בחלון גדול מחלק אחד מתוך N+1 בפרס שאחריו.
    הגנה: עמלה שנשארת גבוהה עד העסקה הראשונה, בלי מועד סיום. אז אין מה לחכות לו.
    """
    sys.path.insert(0, '../01-latency-edge')
    from sim import BASE, draw_month, arb_profit
    p = dict(BASE); rng = np.random.default_rng(seed)
    posts = np.concatenate([draw_month(rng, p) for _ in range(months)])
    Y = p['pool_usd']
    a_base = arb_profit(Y, posts, base)
    a_surge = arb_profit(Y, posts, surge)
    eff = np.maximum(np.abs(posts) - np.log1p(surge), 0)
    fee_rev = surge * Y * np.abs(np.exp(eff / 2) - 1)
    gap = np.sign(posts) * np.minimum(np.abs(posts), np.log1p(surge))
    lp_if_trade = a_surge + arb_profit(Y, gap, base) - fee_rev
    out = []
    for n in n_comp_list:
        trade_now = a_surge > a_base / (n + 1)
        lp_window = np.where(trade_now, lp_if_trade, a_base)
        out.append(dict(n_arbs=n + 1,
                        lp_no_defense=float(a_base.sum() / months),
                        lp_window_fee=float(lp_window.sum() / months),
                        lp_until_first_trade=float(lp_if_trade.sum() / months),
                        share_posts_waited=float(1 - trade_now[a_base > 0].mean())))
    return out


# ---------------------------------------------------------------- run everything
def main():
    TRAIN = list(range(100, 106))     # זרעים לחיפוש
    TEST = list(range(500, 530))      # זרעים נפרדים לבדיקה, כדי לא להתאים יתר על המידה
    res = {}
    mech0 = dict(DEFAULT_MECH)
    std = dict(DEFAULT_MECH, fair=False)

    print('baseline (no attacker)')
    res['baseline'] = {'standard': evaluate(None, std, TEST), 'regret': evaluate(None, mech0, TEST)}
    print(' ', res['baseline'])

    # A1: adaptive sniper (hold longer to dodge the flip penalty)
    sp = {'sell_t': (1, 200)}
    mk = lambda x: {'type': 'sniper', 'budget': 5.0, 'sell_t': x['sell_t']}
    naive = {'type': 'sniper', 'budget': 5.0, 'sell_t': 10}
    b_std = evolve(sp, mk, std, TRAIN, rng_seed=1)
    b_fair = evolve(sp, mk, mech0, TRAIN, rng_seed=2)
    res['A1_sniper'] = dict(
        naive_sell10_standard=evaluate(naive, std, TEST), naive_sell10_regret=evaluate(naive, mech0, TEST),
        best_vs_standard=dict(params=b_std[1], **evaluate(mk(b_std[1]), std, TEST)),
        best_vs_regret=dict(params=b_fair[1], **evaluate(mk(b_fair[1]), mech0, TEST)))
    print('A1', json.dumps(res['A1_sniper'], ensure_ascii=False))

    # A2: transfer to a fresh wallet to reset cost basis
    sp = {'transfer_t': (1, 120), 'sell_gap': (1, 60)}
    for rule in ('reset', 'carry'):
        mk = lambda x, rule=rule: {'type': 'transfer', 'budget': 5.0, 'rule': rule, **x}
        b = evolve(sp, mk, mech0, TRAIN, rng_seed=3)
        res[f'A2_transfer_{rule}'] = dict(params=b[1], **evaluate(mk(b[1]), mech0, TEST))
        print('A2', rule, res[f'A2_transfer_{rule}'])

    # A3: wash-loss farming: two own wallets, one wins and is taxed lightly, one loses and claims a rebate
    sp = {'tA': (0, 250), 'd': (1, 20), 'e': (1, 30), 'g': (1, 60), 'bA': (0.5, 30.0), 'bB': (0.5, 30.0)}
    mkw = lambda x: {'type': 'wash', **x}
    defenses = {
        'original': mech0,
        'min_hold_30': dict(mech0, rebate_min_hold=30),
        'cap30_floor30': dict(mech0, cap=0.3, floor=0.3),
        'cap20_floor20': dict(mech0, cap=0.2, floor=0.2),
    }
    res['A3_wash'] = {}
    for name, mech in defenses.items():
        b = evolve(sp, mkw, mech, TRAIN, rng_seed=4)
        ev = evaluate(mkw(b[1]), mech, TEST)
        clean = evaluate(None, mech, TEST)
        ctrl = evaluate(mkw(dict(b[1], bB=0.0)), mech, TEST)
        res['A3_wash'][name] = dict(params=b[1], attacked=ev, control_no_loser_wallet=ctrl, no_attacker=clean,
                                    wash_gain=ev['atk_net'] - ctrl['atk_net'])
        print('A3', name, json.dumps(res['A3_wash'][name], ensure_ascii=False))

    # B: news fee with strategic waiting
    res['B_news_fee'] = news_fee_game([0, 1, 2, 4, 9, 24])
    for x in res['B_news_fee']: print('B', x)

    with open('results.json', 'w') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
