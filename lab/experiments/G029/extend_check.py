#!/usr/bin/env python3
"""For a good colouring of [1,n], count for each colour c how many monochromatic k-APs
appear if position n+1 gets colour c (append) or a new position 0 gets c (prepend).
Usage: extend_check.py CERT r k"""
import sys
from verify import load
col = load(sys.argv[1]); r, k = int(sys.argv[2]), int(sys.argv[3]); n = len(col)
c = [None] + col
def count_end(cc, x, arr, n):
    t = 0
    for d in range(1, (x - 1) // (k - 1) + 1):
        if all(arr[x - i * d] == cc for i in range(1, k)): t += 1
    return t
app = [count_end(cc, n + 1, c + [None], n) for cc in range(r)]
rev = [None] + col[::-1]
pre = [count_end(cc, n + 1, rev + [None], n) for cc in range(r)]
print(f"n={n}: append counts per colour {app}; prepend counts {pre}")
