#!/usr/bin/env python3
"""Explicit Kim palette product (arXiv:2610.32000, Thm 2.1):
   chi(q*t + u) = phi_u(beta(t)),  0 <= u < q, 0 <= t < n,
with S(u) an s-subset of [r] (palette, from palette_sat.py), phi_u the order-preserving
bijection [s] -> S(u), and beta an AP-free s-colouring of length n (certificate file).
Writes chi on 1-indexed positions 1..q*n (position x <-> integer x-1).
Usage: kim_product.py r s k q BETA_FILE OUT [tlim]"""
import sys, json
from palette_sat import solve
from verify import load
r, s, k, q = map(int, sys.argv[1:5]); beta = load(sys.argv[5]); out = sys.argv[6]
tl = float(sys.argv[7]) if len(sys.argv) > 7 else 60
info, S = solve(r, s, k, q, tl)
assert S is not None, info
assert all(len(x) == s for x in S)
n = len(beta)
chi = [S[u][beta[t]] for t in range(n) for u in range(q)]   # index q*t+u
open(out, 'w').write(''.join(map(str, chi)) + '\n')
json.dump({"r": r, "s": s, "k": k, "q": q, "n_base": n, "len": q * n, "S": S, "base": sys.argv[5]},
          open(out + '.json', 'w'))
print(json.dumps({"r": r, "k": k, "q": q, "n_base": n, "len": q * n}))
