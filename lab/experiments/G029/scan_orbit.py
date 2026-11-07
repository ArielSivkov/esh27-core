#!/usr/bin/env python3
"""Scan the orbit-CSP family for a cell (r,k) above its record.
For all m = z*p with record < (k-1)m+1 and m <= fac*m_rec, z <= zmax, gcd(z,p)=1,
R | p-1 with 2 <= R <= Rmax: solve the CSP; on SAT run the full pipeline (build, repair,
two verifiers, save certificate).  Checkpoints each (p,z,R) to scans/scan_r{r}_k{k}.jsonl
and skips finished ones on restart.  Usage: scan_orbit.py r k record fac zmax Rmax"""
import sys, json, os, time, math
from construct import primes_upto
from orbit_csp import solve
import pipeline

r, k, record, fac, zmax, Rmax = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, 'scans', f'scan_r{r}_k{k}.jsonl')
done = set()
if os.path.exists(out):
    for line in open(out):
        d = json.loads(line); done.add((d['p'], d['z'], d['R']))
mrec = (record - 1) / (k - 1)
mmax = int(fac * mrec)
jobs = []
for z in range(1, zmax + 1):
    for p in primes_upto(mmax // z + 1):
        p = int(p)
        if p <= k or math.gcd(z, p) != 1: continue
        m = z * p
        if (k - 1) * m + 1 <= record or m > mmax: continue
        for R in range(2, Rmax + 1):
            if (p - 1) % R == 0 and (p, z, R) not in done:
                jobs.append((m, p, z, R))
jobs.sort()
print(f"cell W({r},{k}) record {record}: {len(jobs)} jobs, m in ({mrec:.0f}, {mmax}]", flush=True)
t0 = time.time(); nsat = 0
with open(out, 'a') as fh:
    for (m, p, z, R) in jobs:
        info, f = solve(r, k, p, z, R)
        rec = {"p": p, "z": z, "R": R, "m": m, "len": info["len"], "status": info["status"], "t": info.get("t")}
        if f is not None:
            nsat += 1
            full = pipeline.run(r, k, p, z, R, record, save=True)
            rec.update(n_good=full.get("n_good"), beats=full.get("beats_record"), cert=full.get("cert"), fstr=full.get("f"))
            print("SAT", json.dumps(rec), flush=True)
        fh.write(json.dumps(rec) + "\n"); fh.flush()
print(f"done W({r},{k}): {len(jobs)} jobs, {nsat} SAT, {time.time()-t0:.0f}s", flush=True)
