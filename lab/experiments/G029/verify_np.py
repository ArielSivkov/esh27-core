#!/usr/bin/env python3
"""Verifier 3 (numpy, vectorised per difference d).  For each d: e = (c[d:] == c[:-d]);
a monochromatic k-AP with difference d starting at a exists iff e[a], e[a+d], ...,
e[a+(k-2)d] are all True.  Usage: verify_np.py FILE r k"""
import sys, numpy as np
from verify import load
c = np.array(load(sys.argv[1]), dtype=np.int8); r, k = int(sys.argv[2]), int(sys.argv[3]); n = len(c)
assert c.min() >= 0 and c.max() < r
for d in range(1, (n - 1) // (k - 1) + 1):
    e = c[d:] == c[:-d]                 # length n-d ; e[a] <=> c[a] == c[a+d]
    m = n - (k - 1) * d                 # number of start positions
    acc = e[:m].copy()
    for i in range(1, k - 1):
        acc &= e[i * d:i * d + m]
        if not acc.any(): break
    if acc.any():
        a = int(np.argmax(acc)); print(f"FAIL n={n} r={r} k={k}: monochromatic AP a={a+1} d={d}"); sys.exit(1)
print(f"OK n={n} r={r} k={k}: no monochromatic {k}-AP (numpy)")
