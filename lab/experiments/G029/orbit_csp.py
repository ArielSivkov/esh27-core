#!/usr/bin/env python3
"""Generalised power-residue / zipper family, solved exactly as a small SAT problem.

Cyclic colouring of Z_m, m = z*p (p prime, gcd(z,p)=1).  Class of x (x mod p != 0):
    (x mod z, dlog(x mod p) mod R)        R | p-1
Colour = f(class) with f : classes -> [r] ARBITRARY (Rabung: z=1, R=r, f = id;
Rabung-Lotts zippers: special f with z=2,3).  Integers = 0 mod p are wildcard slots
(handled afterwards by lsearch on the integer colouring).
The integer colouring of {0..(k-1)m} has no monochromatic k-AP avoiding wildcard slots
iff no cyclic k-AP of Z_m with difference d in [1, m-1] avoiding 0 mod p is monochromatic.
Since multiplying by h (h = 1 mod z, h mod p an R-th power) preserves classes, only one
d per orbit is needed.  Constraint per AP: 'not all equal' on the set of its classes.
APs through a wildcard slot impose 'not all equal' on their other elements.
Usage: orbit_csp.py r k p z R [time_s]   -> prints JSON; writes f to stdout if SAT."""
import sys, json, time
import numpy as np
from pysat.solvers import Cadical153
from construct import dlog_table

def classes(p, z, R):
    L = dlog_table(p); m = z * p; x = np.arange(m)
    cl = (x % z) * R + (L[x % p] % R)
    cl[x % p == 0] = -1
    return cl

def build_constraints(p, z, R, k):
    m = z * p; cl = classes(p, z, R)
    # orbit representatives of d in Z_m \ {0} under multiplication by H
    seen = np.zeros(m, bool); reps = []
    L = dlog_table(p)
    g_R = None
    # H generators: h with h = 1 mod z and h = g^R mod p  (CRT)
    from construct import primroot
    g = primroot(p); hp = pow(g, R, p)
    # CRT: h = 1 mod z, h = hp mod p
    h = next(t for t in range(m) if t % z == 1 % z and t % p == hp) if z > 1 else hp
    order = (p - 1) // R
    for d in range(1, m):
        if seen[d]: continue
        reps.append(d); y = d
        for _ in range(order):
            seen[y] = True; y = y * h % m
    a = np.arange(m)[:, None]; i = np.arange(k)[None, :]
    cons = set(); trivial = False
    for d in reps:
        pts = (a + i * d) % m              # m x k
        c = np.sort(cl[pts], axis=1)
        # APs through a wildcard slot: the remaining non-wildcard elements must be
        # non-monochromatic (Rabung's condition; the slot colour cannot repair all d).
        # APs consisting only of wildcard slots are left to the integer-level repair.
        for row in np.unique(c, axis=0):
            st = set(row.tolist()); st.discard(-1)
            if not st: continue
            if len(st) == 1: trivial = True; break
            cons.add(tuple(sorted(st)))
        if trivial: break
    return cl, cons, trivial, len(reps)

def solve(r, k, p, z, R, tlim=60):
    t0 = time.time()
    cl, cons, trivial, nreps = build_constraints(p, z, R, k)
    info = {"r": r, "k": k, "p": p, "z": z, "R": R, "m": z * p, "len": (k - 1) * z * p + 1,
            "nreps": nreps, "ncons": len(cons)}
    if trivial:
        info.update(status="UNSAT-trivial", t=round(time.time() - t0, 2)); return info, None
    V = z * R; var = lambda v, c: int(v) * r + c + 1
    s = Cadical153()
    for v in range(V): s.add_clause([var(v, c) for c in range(r)])
    s.add_clause([var(cl[1], 0)])            # colour symmetry
    for con in cons:
        for c in range(r): s.add_clause([-var(v, c) for v in con])
    import threading
    timer = threading.Timer(tlim, s.interrupt); timer.start()
    res = s.solve_limited(expect_interrupt=True); timer.cancel()
    info["t"] = round(time.time() - t0, 2)
    if res is None:
        info["status"] = "UNKNOWN-timeout"; return info, None
    if not res:
        info["status"] = "UNSAT"; return info, None
    model = set(x for x in s.get_model() if x > 0)
    f = [next(c for c in range(r) if var(v, c) in model) for v in range(V)]
    info["status"] = "SAT"; return info, f

if __name__ == '__main__':
    r, k, p, z, R = map(int, sys.argv[1:6])
    info, f = solve(r, k, p, z, R, float(sys.argv[6]) if len(sys.argv) > 6 else 60)
    print(json.dumps(info)); 
    if f: print("f=" + ''.join(map(str, f)))
