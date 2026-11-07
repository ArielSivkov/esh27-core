#!/usr/bin/env python3
"""Power-residue k-polychromatic blocks (Kim arXiv:2610.32000, Cor. 2.2) for SMALL k.
m(u) = dlog(u) mod h on Z_q^* (q prime, h | q-1), m(0) arbitrary.  By dilation, m is
k-polychromatic iff every cyclic window {a,...,a+k-1} (0 removed) meets all h classes.
Prints, per (k,h), the largest such q <= qmax, and the implied bounds
W(r,k) > q * L(r - ceil(r/h), k) for r = 3..6 where L = length of a base colouring we hold.
Usage: kim_blocks.py qmax"""
import sys, json, math
import numpy as np
from construct import primes_upto, dlog_table
qmax = int(sys.argv[1])
def poly(q, h, k):
    L = dlog_table(q) % h
    seq = np.concatenate([L[1:], L[1:k]])  # residues 1..q-1 then wrap; windows through 0 handled below
    for a in range(q):
        w = [(a + i) % q for i in range(k)]
        cols = set(int(L[x]) for x in w if x != 0)
        if len(cols) < h: return False
    return True
res = {}
P = [int(p) for p in primes_upto(qmax)]
for k in range(4, 9):
    for h in range(2, 7):
        good = [q for q in P if q > k and (q - 1) % h == 0 and poly(q, h, k)]
        res[(k, h)] = good
        print(json.dumps({"k": k, "h": h, "n_good": len(good), "largest": good[-3:]}), flush=True)
json.dump({f"{k},{h}": v for (k, h), v in res.items()}, open('scans/kim_blocks.json', 'w'))
