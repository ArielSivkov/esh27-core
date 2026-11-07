#!/usr/bin/env python3
"""Direct SAT for an AP-free r-colouring of [1,n] (CaDiCaL, hard time limit).
Optional symmetry: reflection  c(n+1-x) = (c(x) + s) mod r   (--refl s).
Optional hint: --fix FILE M  keeps positions of FILE fixed except a window of M free
positions at each end (extend-and-repair).
Usage: sat_direct.py r k n tlim OUT [--refl s] [--fix FILE M]"""
import sys, subprocess, os, time, json
CADICAL = '/home/user/esh27-core/lab/experiments/G050/tools/cadical/build/cadical'
SCR = os.environ.get('G029_SCRATCH', '/tmp/claude-0/-home-user/647f98b9-61ad-591f-af35-53bff0238e34/scratchpad')
a = sys.argv; r, k, n, tlim, out = int(a[1]), int(a[2]), int(a[3]), int(a[4]), a[5]
refl = int(a[a.index('--refl') + 1]) if '--refl' in a else None
fix = (a[a.index('--fix') + 1], int(a[a.index('--fix') + 2])) if '--fix' in a else None
v = lambda x, c: (x - 1) * r + c + 1
cl = []
for x in range(1, n + 1):
    cl.append([v(x, c) for c in range(r)])
    for c in range(r):
        for c2 in range(c + 1, r): cl.append([-v(x, c), -v(x, c2)])
for d in range(1, (n - 1) // (k - 1) + 1):
    for s in range(1, n - (k - 1) * d + 1):
        for c in range(r): cl.append([-v(s + i * d, c) for i in range(k)])
if refl is not None:
    for x in range(1, n + 1):
        y = n + 1 - x
        for c in range(r): cl.append([-v(x, c), v(y, (c + refl) % r)])
else:
    cl.append([v(1, 0)])
if fix:
    s0 = [int(ch) for ch in open(fix[0]).read().strip()]
    M = fix[1]
    for x in range(1 + M, n + 1 - M):
        if x - 1 < len(s0): cl.append([v(x, s0[x - 1])])
cnf = os.path.join(SCR, f'direct_{r}_{k}_{n}_{os.getpid()}.cnf')
with open(cnf, 'w') as fh:
    fh.write(f'p cnf {n * r} {len(cl)}\n')
    for c in cl: fh.write(' '.join(map(str, c)) + ' 0\n')
t0 = time.time()
pr = subprocess.run([CADICAL, '-q', '-t', str(tlim), cnf], capture_output=True, text=True)
os.unlink(cnf)
st = 'SAT' if 's SATISFIABLE' in pr.stdout else 'UNSAT' if 's UNSATISFIABLE' in pr.stdout else 'UNKNOWN'
res = {"method": "sat-direct", "r": r, "k": k, "n": n, "refl": refl, "fix": fix, "status": st, "t": round(time.time() - t0, 1), "nclauses": len(cl)}
if st == 'SAT':
    m = set(int(t) for line in pr.stdout.splitlines() if line.startswith('v') for t in line[1:].split() if int(t) > 0)
    col = [next(c for c in range(r) if v(x, c) in m) for x in range(1, n + 1)]
    open(out, 'w').write(''.join(map(str, col)) + '\n')
print(json.dumps(res))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runs.jsonl'), 'a') as fh:
    res["timestamp"] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()); fh.write(json.dumps(res) + '\n')
