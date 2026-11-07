#!/usr/bin/env python3
"""Scan primes p: does the Rabung power-residue colouring of Z_p (colour = dlog mod r)
satisfy the cyclic window condition for k-APs?  Prints the largest good p and the
implied length (k-1)p+1.  Usage: scan_rabung.py r k pmax"""
import sys, json, numpy as np
from construct import primes_upto, rabung_cyclic

def good(p, r, k):
    c = rabung_cyclic(p, r)              # c[0] = -1 (wildcard)
    s = c[1:]                            # residues 1..p-1
    # runs of >= k equal colours inside 1..p-1
    eq = (s[1:] == s[:-1]).astype(np.int8)
    # run of k equal <=> k-1 consecutive eq's
    if k - 1 <= len(eq):
        w = np.convolve(eq, np.ones(k - 1, np.int8), 'valid')
        if (w >= k - 1).any(): return False
    # windows through 0: residues p-j..p-1 and 1..k-1-j  (k-1 elements)
    for j in range(k):
        el = [c[(p - j + t) % p] for t in range(k) if (p - j + t) % p != 0]
        if all(e == el[0] for e in el): return False
    return True

if __name__ == '__main__':
    r, k, pmax = map(int, sys.argv[1:4])
    goods = [int(p) for p in primes_upto(pmax) if p > k and (p - 1) % r == 0 and good(int(p), r, k)]
    print(json.dumps({"r": r, "k": k, "pmax": pmax, "n_good": len(goods),
                      "largest_good": goods[-5:], "implied_len": (k - 1) * goods[-1] + 1 if goods else None}))
