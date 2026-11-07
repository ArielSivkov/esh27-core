"""Method C (independent of both C programs): SAT model enumeration with PySAT (CaDiCaL/Glucose),
plus pure brute force over all k^n maps for small n.
Unordered count = number of models of the CNF with restricted-growth-string symmetry breaking
(colour c>0 may be used at i only if colour c-1 was used at some j<i).
Convention: weak=False forbids monochromatic x+y=z for all 1<=x<=y (x=y allowed);
            weak=True  forbids it only for x<y."""
import sys, itertools, time
from pysat.solvers import Solver

def cnf(k, n, weak, rgs):
    v = lambda i, c: (i - 1) * k + c + 1
    cl = []
    for i in range(1, n + 1):
        cl.append([v(i, c) for c in range(k)])
        for a in range(k):
            for b in range(a + 1, k):
                cl.append([-v(i, a), -v(i, b)])
    for x in range(1, n + 1):
        for y in range(x, n + 1 - x):
            if weak and x == y: continue
            for c in range(k):
                cl.append(sorted({-v(x, c), -v(y, c), -v(x + y, c)}))
    if rgs:
        for i in range(1, n + 1):
            for c in range(1, k):
                cl.append([-v(i, c)] + [v(j, c - 1) for j in range(1, i)])
    return cl, n * k

def count_models(k, n, weak, rgs):
    cl, nv = cnf(k, n, weak, rgs)
    cnt = 0
    with Solver(name='cadical153', bootstrap_with=cl) as s:
        while s.solve():
            m = s.get_model()
            cnt += 1
            s.add_clause([-l for l in m[:nv] if l > 0])
    return cnt

def brute_labelled(k, n, weak):
    trip = [(x, y) for x in range(1, n + 1) for y in range(x, n + 1 - x) if not (weak and x == y)]
    t = 0
    for col in itertools.product(range(k), repeat=n):
        if all(not (col[x-1] == col[y-1] == col[x+y-1]) for x, y in trip):
            t += 1
    return t

if __name__ == '__main__':
    k, weak = int(sys.argv[1]), sys.argv[2] == 'weak'
    ns = [int(a) for a in sys.argv[3].split(',')]
    mode = sys.argv[4]  # 'unl' | 'lab' | 'brute'
    for n in ns:
        t0 = time.time()
        if mode == 'unl': r = count_models(k, n, weak, True)
        elif mode == 'lab': r = count_models(k, n, weak, False)
        else: r = brute_labelled(k, n, weak)
        print(n, r, f"{time.time()-t0:.2f}s", flush=True)
