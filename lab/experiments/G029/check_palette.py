#!/usr/bin/env python3
"""Independent check of Kim's condition (*) for a palette JSON {r,s,k,q,S}: every S(u) has
s elements of [r], and no A_c = {u : c in S(u)} contains a k-AP of Z_q with d != 0 mod q.
Usage: check_palette.py FILE.json"""
import sys, json
P = json.load(open(sys.argv[1])); r, s, k, q, S = P['r'], P['s'], P['k'], P['q'], P['S']
assert len(S) == q and all(len(set(x)) == s and all(0 <= c < r for c in x) for x in S)
for c in range(r):
    A = [c in S[u] for u in range(q)]
    for d in range(1, q):
        for a in range(q):
            if all(A[(a + i * d) % q] for i in range(k)):
                print(f"FAIL colour {c}: AP a={a} d={d}"); sys.exit(1)
print(f"OK palette r={r} s={s} k={k} q={q}: condition (*) holds; S={''.join(''.join(map(str,x))+'|' for x in S)}")
