#!/usr/bin/env python3
"""Build the integer Rabung colouring of {0..(k-1)p} (written 1-indexed, length (k-1)p+1),
fill the k zero slots (integers j*p) with colour(j) (colour(0):=0), write digits to OUT.
Usage: build_rabung.py r k p OUT"""
import sys
from construct import rabung_cyclic, integer_colouring
r, k, p, out = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
cyc = rabung_cyclic(p, r)
fill = lambda t: max(int(cyc[(t // p) % p]), 0)
col = integer_colouring(cyc, k, fill)
open(out, 'w').write(''.join(map(str, col)) + '\n')
print(len(col))
