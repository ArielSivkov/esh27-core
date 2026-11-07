#!/usr/bin/env python3
"""Sweep Kim palette blocks for small cells: W(r,k) > q*n(s,k) where n(s,k) is the length
of an AP-free s-colouring we HOLD (so the product is explicit).  Logs to scans/palette.jsonl."""
import json, os, sys
from palette_sat import solve
HERE = os.path.dirname(os.path.abspath(__file__))
# lengths of explicit base colourings available (exact W-1 or our reproduced certificates)
base = {(2,3):8,(3,3):26,(4,3):75,(5,3):170,(2,4):34,(3,4):292,(4,4):1048,(5,4):2254,(2,5):177,(3,5):2173,(4,5):17705,(2,6):696,(2,7):3703,(2,8):11495}
exactW = {(2,3):9,(3,3):27,(4,3):76,(2,4):35,(3,4):293,(2,5):178,(2,6):1132}
record = {(5,3):170,(6,3):225,(4,4):1048,(5,4):2254,(6,4):9778,(3,5):2173,(4,5):17705,(5,5):98741,(6,5):98748,(3,6):11191,(3,7):48811,(3,8):238400}
qcap = int(sys.argv[1]) if len(sys.argv) > 1 else 60
out = open(os.path.join(HERE, 'scans', 'palette.jsonl'), 'a')
for (r, k), rec in record.items():
    for s in range(2, r):
        if (s, k) not in base: continue
        n = base[(s, k)]
        qmin = rec // n + 1
        # Kim Prop 6.1: W(r-s+1,k) > (k-1) q
        W = exactW.get((r - s + 1, k))
        qmax = min(qcap, (W - 1) // (k - 1)) if W else qcap
        for q in range(max(qmin, 2), qmax + 1):
            info, S = solve(r, s, k, q, 30)
            info.update(n=n, bound=q * n, record=rec)
            if S: info["S"] = S
            out.write(json.dumps(info) + "\n"); out.flush()
            if info["status"] != "UNSAT": print(json.dumps(info)[:300], flush=True)
        print(f"W({r},{k}) s={s} n={n}: q in [{qmin},{qmax}] done", flush=True)
