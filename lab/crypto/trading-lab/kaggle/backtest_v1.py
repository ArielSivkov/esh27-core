"""ESH27 trading lab — backtest v1 (paper only, no real money, no exchange accounts).

Honest walk-forward test of classic rule-based strategies on historical prices:
- Signals are computed on bar t and executed on bar t+1 (no lookahead).
- Fees are charged on every position change.
- Parameters are picked on the first 60% of each series (in-sample) and judged on the last 40% (out-of-sample).
- A random-strategy baseline shows how much of the out-of-sample result luck alone would give.
CPU only. Output: results.json + report.md in /kaggle/working.
"""
import glob
import json
import os

import numpy as np
import pandas as pd

RNG = np.random.default_rng(27)
OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else "."
TRAIN_FRAC = 0.6


def find(name):
    hits = [p for p in glob.glob("/kaggle/input/**/" + name, recursive=True)]
    return hits[0] if hits else None


def load_binance(path):
    d = pd.read_csv(path)
    d["t"] = pd.to_datetime(d["Open time"].str.replace(" UTC", ""), errors="coerce")
    return d.set_index("t")["Close"].astype(float).dropna()


def load_coingecko(path):
    d = pd.read_csv(path)
    d["t"] = pd.to_datetime(d["date"], errors="coerce")
    s = d.set_index("t")["price"].astype(float)
    return s[s > 0].dropna()


def load_stooq(path):
    d = pd.read_csv(path)
    d["t"] = pd.to_datetime(d["Date"], errors="coerce")
    return d.set_index("t")["Close"].astype(float).dropna()


# ---------- strategies: return position series in {0,1}, decided at bar close ----------
def sma_cross(p, fast, slow):
    return (p.rolling(fast).mean() > p.rolling(slow).mean()).astype(float)


def tsmom(p, lb):
    return (p / p.shift(lb) - 1 > 0).astype(float)


def donchian(p, n):
    hi, lo = p.rolling(n).max().shift(1), p.rolling(max(2, n // 2)).min().shift(1)
    pos = np.zeros(len(p))
    for i in range(len(p)):
        prev = pos[i - 1] if i else 0
        if p.iloc[i] > hi.iloc[i]:
            pos[i] = 1
        elif p.iloc[i] < lo.iloc[i]:
            pos[i] = 0
        else:
            pos[i] = prev
    return pd.Series(pos, index=p.index)


def rsi(p, n):
    d = p.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def rsi_mr(p, n, lo, hi):
    r = rsi(p, n)
    pos = np.zeros(len(p))
    for i in range(len(p)):
        prev = pos[i - 1] if i else 0
        if r.iloc[i] < lo:
            pos[i] = 1
        elif r.iloc[i] > hi:
            pos[i] = 0
        else:
            pos[i] = prev
    return pd.Series(pos, index=p.index)


FAMILIES = {
    "buy_hold": [({}, lambda p: pd.Series(1.0, index=p.index))],
    "sma_cross": [({"fast": f, "slow": s}, (lambda f, s: lambda p: sma_cross(p, f, s))(f, s))
                  for f in (5, 10, 20, 50) for s in (50, 100, 200) if f < s],
    "tsmom": [({"lookback": lb}, (lambda lb: lambda p: tsmom(p, lb))(lb)) for lb in (20, 60, 120, 250)],
    "donchian": [({"n": n}, (lambda n: lambda p: donchian(p, n))(n)) for n in (20, 55, 100)],
    "rsi_mr": [({"n": n, "lo": lo, "hi": hi}, (lambda n, lo, hi: lambda p: rsi_mr(p, n, lo, hi))(n, lo, hi))
               for n in (2, 14) for lo in (10, 30) for hi in (50, 70)],
}


def run(p, pos, fee):
    """Execute next bar; returns strategy per-bar returns."""
    ret = p.pct_change().fillna(0)
    held = pos.shift(1).fillna(0)
    trades = held.diff().abs().fillna(held.iloc[0])
    return held * ret - trades * fee, trades


def metrics(r, trades, ppy):
    r = r.dropna()
    if len(r) < 10:
        return None
    eq = (1 + r).cumprod()
    years = len(r) / ppy
    cagr = eq.iloc[-1] ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    sd = r.std()
    sharpe = float(r.mean() / sd * np.sqrt(ppy)) if sd > 0 else 0.0
    dd = float((eq / eq.cummax() - 1).min())
    return {"cagr": round(float(cagr), 4), "sharpe": round(sharpe, 3), "max_dd": round(dd, 4),
            "total_return": round(float(eq.iloc[-1] - 1), 4), "trades": int(trades.sum()),
            "exposure": None}


def random_baseline(p, fee, ppy, n=500, hold=20):
    """Random long/flat switching with the given mean holding time; OOS Sharpe distribution."""
    k = int(len(p) * TRAIN_FRAC)
    sh = []
    for _ in range(n):
        sw = RNG.random(len(p)) < 1 / hold
        state = np.cumsum(sw) % 2
        pos = pd.Series(state.astype(float), index=p.index)
        r, t = run(p, pos, fee)
        m = metrics(r.iloc[k:], t.iloc[k:], ppy)
        if m:
            sh.append(m["sharpe"])
    return np.array(sh)


def assets():
    out = []
    f = find("btc_1d_data_2018_to_2025.csv")
    if f:
        out.append(("BTC 1d (Binance)", load_binance(f), 0.001, 365))
    f = find("btc_4h_data_2018_to_2025.csv")
    if f:
        out.append(("BTC 4h (Binance)", load_binance(f), 0.001, 365 * 6))
    for coin in ("ethereum", "solana", "binancecoin", "cardano", "dogecoin", "chainlink"):
        f = find(coin + ".csv")
        if f:
            out.append((coin + " 1d (CoinGecko)", load_coingecko(f), 0.001, 365))
    for etf in ("spy", "qqq", "iwm", "dia"):
        f = find(etf + ".us.txt")
        if f:
            out.append((etf.upper() + " 1d (US ETF)", load_stooq(f), 0.0005, 252))
    for st in ("aapl", "msft", "jpm", "xom"):
        f = find(st + ".us.txt")
        if f:
            out.append((st.upper() + " 1d (US stock)", load_stooq(f), 0.0005, 252))
    return out


def main():
    results = []
    for name, p, fee, ppy in assets():
        p = p[~p.index.duplicated()].sort_index()
        k = int(len(p) * TRAIN_FRAC)
        row = {"asset": name, "bars": len(p), "start": str(p.index[0].date()), "split": str(p.index[k].date()),
               "end": str(p.index[-1].date()), "fee": fee, "families": {}}
        best_overall = None
        for fam, variants in FAMILIES.items():
            best = None
            for params, fn in variants:
                pos = fn(p)
                r, t = run(p, pos, fee)
                mi = metrics(r.iloc[:k], t.iloc[:k], ppy)
                if mi is None:
                    continue
                if best is None or mi["sharpe"] > best["in_sample"]["sharpe"]:
                    mo = metrics(r.iloc[k:], t.iloc[k:], ppy)
                    best = {"params": params, "in_sample": mi, "out_of_sample": mo,
                            "exposure_oos": round(float(pos.shift(1).iloc[k:].mean()), 3)}
            row["families"][fam] = best
            if fam != "buy_hold" and best and (best_overall is None or
                                               best["in_sample"]["sharpe"] > best_overall[1]["in_sample"]["sharpe"]):
                best_overall = (fam, best)
        rb = random_baseline(p, fee, ppy)
        chosen = best_overall[1]["out_of_sample"]["sharpe"] if best_overall else None
        row["picked_in_sample"] = {"family": best_overall[0], **best_overall[1]} if best_overall else None
        row["random_oos_sharpe"] = {"p50": round(float(np.median(rb)), 3), "p95": round(float(np.percentile(rb, 95)), 3)}
        row["picked_percentile_vs_random"] = round(float((rb < chosen).mean() * 100), 1) if chosen is not None else None
        row["beats_buy_hold_oos"] = bool(chosen is not None and chosen > row["families"]["buy_hold"]["out_of_sample"]["sharpe"])
        results.append(row)
        print(name, "picked:", best_overall[0] if best_overall else None, "OOS sharpe", chosen,
              "B&H", row["families"]["buy_hold"]["out_of_sample"]["sharpe"], "pct vs random", row["picked_percentile_vs_random"])

    json.dump({"version": "backtest_v1", "train_frac": TRAIN_FRAC, "results": results},
              open(os.path.join(OUT, "results.json"), "w"), indent=1)
    lines = ["# Backtest v1 — out-of-sample summary", "",
             "| asset | OOS period | picked (in-sample) | OOS Sharpe | B&H OOS Sharpe | OOS max DD | random p95 | beats B&H |",
             "|---|---|---|---|---|---|---|---|"]
    for r in results:
        pk = r["picked_in_sample"]
        bh = r["families"]["buy_hold"]["out_of_sample"]
        lines.append(f"| {r['asset']} | {r['split']}→{r['end']} | {pk['family']} {pk['params']} | "
                     f"{pk['out_of_sample']['sharpe']} | {bh['sharpe']} | {pk['out_of_sample']['max_dd']} | "
                     f"{r['random_oos_sharpe']['p95']} | {'yes' if r['beats_buy_hold_oos'] else 'no'} |")
    open(os.path.join(OUT, "report.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
