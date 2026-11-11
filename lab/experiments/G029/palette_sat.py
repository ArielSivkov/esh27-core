#!/usr/bin/env python3
"""Kim (arXiv:2610.32000, Thm 2.1, palette form) blocks via SAT.
Find S : Z_q -> s-subsets of [r] such that for every colour c the set
A_c = {u : c in S(u)} contains no k-AP of Z_q with nonzero difference.
Then W(r,k) > q * n for any AP-free s-colouring of n consecutive integers.
Usage: palette_sat.py r s k q [tlim]  -> JSON (+ 'S=' line with the palette if SAT)"""
import sys, json, os, subprocess, time, tempfile
from pysat.card import CardEnc, EncType
CADICAL = '/home/user/esh27-core/lab/experiments/G050/tools/cadical/build/cadical'

def solve(r, s, k, q, tlim=60):
    v = lambda u, c: u * r + c + 1
    top = q * r; cl = []
    for u in range(q):
        enc = CardEnc.equals(lits=[v(u, c) for c in range(r)], bound=s, top_id=top, encoding=EncType.seqcounter)
        top = max(top, enc.nv); cl += enc.clauses
    aps = set()
    for d in range(1, q):
        for a in range(q):
            aps.add(frozenset((a + i * d) % q for i in range(k)))
    for ap in aps:
        for c in range(r): cl.append([-v(u, c) for u in ap])
    cl.append([v(0, c) for c in range(s)])  # weak symmetry: S(0) = {0..s-1}
    for c in range(s): cl.append([v(0, c)])
    fd, cnf = tempfile.mkstemp(suffix='.cnf', dir=os.environ.get('G029_SCRATCH', '/tmp')); os.close(fd)
    with open(cnf, 'w') as fh:
        fh.write(f"p cnf {top} {len(cl)}\n")
        for c in cl: fh.write(' '.join(map(str, c)) + ' 0\n')
    t0 = time.time()
    pr = subprocess.run([CADICAL, '-q', '-t', str(int(tlim)), cnf], capture_output=True, text=True)
    os.unlink(cnf)
    st = 'SAT' if 's SATISFIABLE' in pr.stdout else 'UNSAT' if 's UNSATISFIABLE' in pr.stdout else 'UNKNOWN'
    S = None
    if st == 'SAT':
        m = set(int(t) for line in pr.stdout.splitlines() if line.startswith('v') for t in line[1:].split() if int(t) > 0)
        S = [[c for c in range(r) if v(u, c) in m] for u in range(q)]
    return {"r": r, "s": s, "k": k, "q": q, "status": st, "t": round(time.time() - t0, 2)}, S

if __name__ == '__main__':
    a = list(map(int, sys.argv[1:5])); tl = float(sys.argv[5]) if len(sys.argv) > 5 else 60
    info, S = solve(*a, tl); print(json.dumps(info))
    if S: print("S=" + json.dumps(S))
