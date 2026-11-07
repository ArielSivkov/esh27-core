#!/usr/bin/env python3
"""Structured colourings for vdW lower bounds (Rabung / Rabung-Lotts style).

rabung(p, r): colour of x in Z_p^*  = dlog_g(x) mod r  (power-residue classes; the partition
  does not depend on the primitive root g, only the labelling does).
Integer colouring of {0,...,(k-1)m} (1-indexed position x <-> integer x-1) obtained by
repeating a cyclic colouring of Z_m; the k(k-1)... "zero slots" (integers = 0 mod p) are
left to be fixed by a small local search (lsearch free_mode=p).

zipper(p, z, R, f, r): cyclic colouring of Z_{zp} (gcd(z,p)=1):
  x mod p != 0  ->  f[(x mod z), dlog(x mod p) mod R]   with f : Z_z x Z_R -> [r].
  (z=1, R=r, f = identity is Rabung's colouring.)
"""
import numpy as np

def primes_upto(N):
    s = np.ones(N + 1, bool); s[:2] = False
    for i in range(2, int(N ** .5) + 1):
        if s[i]: s[i * i::i] = False
    return np.nonzero(s)[0]

def factor(n):
    f, d = [], 2
    while d * d <= n:
        while n % d == 0:
            if d not in f: f.append(d)
            n //= d
        d += 1
    if n > 1 and n not in f: f.append(n)
    return f

def primroot(p):
    fs = factor(p - 1)
    for g in range(2, p):
        if all(pow(g, (p - 1) // q, p) != 1 for q in fs):
            return g

def dlog_table(p):
    g = primroot(p); L = np.full(p, -1, np.int64); x = 1
    for e in range(p - 1):
        L[x] = e; x = x * g % p
    return L

def cyclic_window_ok(cyc, k, zero_wild):
    """cyc: colours of Z_m (np array, -1 = wildcard slot).  True iff every window of k
    consecutive residues (cyclically), after dropping wildcard slots, is non-monochromatic.
    For Rabung colourings (m=p prime) this is equivalent (by unit scaling) to: no k-AP of
    Z_p with nonzero difference is monochromatic apart from the zero slot."""
    m = len(cyc); ext = np.concatenate([cyc, cyc[:k]])
    for s in range(m):
        w = ext[s:s + k]; w = w[w >= 0]
        if len(w) and (w == w[0]).all():
            return False
    return True

def rabung_cyclic(p, r):
    L = dlog_table(p); c = L % r; c[0] = -1
    return c

def zipper_cyclic(p, z, R, f):
    L = dlog_table(p); m = z * p; x = np.arange(m)
    v = L[x % p] % R; u = x % z
    c = np.asarray(f)[u, v]; c[x % p == 0] = -1
    return c

def integer_colouring(cyc, k, fill=None):
    """Colours of integers 0..(k-1)m as a list (position x = integer x-1).  Wildcard slots
    are filled with `fill(j)` for the slot at integer j (default 0)."""
    m = len(cyc); N = (k - 1) * m + 1
    out = []
    for t in range(N):
        c = int(cyc[t % m])
        if c < 0: c = fill(t) if fill else 0
        out.append(c)
    return out
