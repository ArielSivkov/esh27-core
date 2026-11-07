#!/usr/bin/env python3
"""Palette SAT for one (r,s,k) over a list of q (descending priority given by order).
Usage: palette_range.py r s k tlim q1 q2 ...   (appends to scans/palette.jsonl)"""
import sys, json, os
from palette_sat import solve
r, s, k, tl = map(int, sys.argv[1:5]); qs = list(map(int, sys.argv[5:]))
out = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scans', 'palette.jsonl'), 'a')
for q in qs:
    info, S = solve(r, s, k, q, tl)
    if S: info["S"] = S
    out.write(json.dumps(info) + "\n"); out.flush()
    print(f"{r},{s},{k} q={q} {info['status']} {info['t']}s", flush=True)
