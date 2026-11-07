#!/usr/bin/env python3
"""Kim palette blocks r=3, s=2 (= 3-polychromatic blocks) for k=6,7,8 in parallel.
Usage: palette_small.py k qmin qmax tlim"""
import sys, json, os
from palette_sat import solve
k, qmin, qmax, tl = map(int, sys.argv[1:5])
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scans', 'palette.jsonl'), 'a')
for q in range(qmin, qmax + 1):
    info, S = solve(3, 2, k, q, tl)
    if S: info["S"] = S
    out.write(json.dumps(info) + "\n"); out.flush()
    print(json.dumps(info)[:200], flush=True)
