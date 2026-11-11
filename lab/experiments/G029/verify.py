#!/usr/bin/env python3
"""Verifier 1 (pure Python, brute force over (a, d)).

A certificate is a text file whose (non-whitespace, non-comment) characters are the
colours c(1), c(2), ..., c(n) as digits 0..r-1 (r <= 10).  Checks that no k-term AP
a, a+d, ..., a+(k-1)d with 1 <= a, d >= 1, a+(k-1)d <= n is monochromatic
(= G050 APFree r k n c).  Usage: verify.py FILE r k   -> exit 0 iff AP-free.
"""
import sys

def load(path):
    s = []
    for line in open(path):
        if line.startswith('#'):
            continue
        s.extend(ch for ch in line if not ch.isspace())
    return [int(ch) for ch in s]

def first_mono_ap(col, r, k):
    n = len(col)
    c = [None] + col            # 1-indexed
    assert all(0 <= x < r for x in col), "colour out of range"
    for d in range(1, (n - 1) // (k - 1) + 1):
        for a in range(1, n - (k - 1) * d + 1):
            x = c[a]
            for i in range(1, k):
                if c[a + i * d] != x:
                    break
            else:
                return (a, d)
    return None

if __name__ == '__main__':
    path, r, k = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    col = load(path)
    bad = first_mono_ap(col, r, k)
    if bad:
        print(f"FAIL n={len(col)} r={r} k={k}: monochromatic AP a={bad[0]} d={bad[1]}")
        sys.exit(1)
    print(f"OK n={len(col)} r={r} k={k}: no monochromatic {k}-AP; colours used={len(set(col))}")
