#!/usr/bin/env python3
"""Re-run UNKNOWN-timeout CSP jobs from a scan file with a longer SAT time limit,
smallest m first.  Usage: deep_unknown.py r k record tlim max_jobs"""
import sys, json, os
from orbit_csp import solve
import pipeline
r, k, record, tlim, maxj = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5])
HERE = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(HERE, 'scans', f'scan_r{r}_k{k}.jsonl'); out = os.path.join(HERE, 'scans', f'deep_r{r}_k{k}.jsonl')
done = set()
if os.path.exists(out):
    for l in open(out): d = json.loads(l); done.add((d['p'], d['z'], d['R']))
unk = {}
for l in open(src):
    d = json.loads(l)
    key = (d['p'], d['z'], d['R'])
    if d['status'].startswith('UNKNOWN'): unk[key] = d['m']
    else: unk.pop(key, None)
jobs = sorted((m, key) for key, m in unk.items() if key not in done)[:maxj]
print(f"deep W({r},{k}): {len(jobs)} jobs tlim={tlim}", flush=True)
with open(out, 'a') as fh:
    for m, (p, z, R) in jobs:
        info, f = solve(r, k, p, z, R, tlim)
        rec = {"p": p, "z": z, "R": R, "m": m, "len": info["len"], "status": info["status"], "t": info.get("t"), "tlim": tlim}
        if f is not None:
            full = pipeline.run(r, k, p, z, R, record, save=True, f=f, info=info)
            rec.update(n_good=full.get("n_good"), beats=full.get("beats_record"), cert=full.get("cert"))
        print(json.dumps(rec), flush=True); fh.write(json.dumps(rec) + "\n"); fh.flush()
