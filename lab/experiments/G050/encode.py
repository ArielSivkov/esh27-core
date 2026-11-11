"""G050 -- CNF encoders for Schur and van der Waerden instances.

Conventions (identical to the Lean formalization in lean/EshLab/Targets/G050/):
  * we colour the integers 1..n with colours 0..k-1;
  * variable  v(i, j)  (1 <= i <= n, 0 <= j < k)  means  "i has colour j";
    DIMACS index  v(i, j) = (i - 1) * k + j + 1.

Schur(k, n): every i gets at least one colour, and for all x, y >= 1 with
x <= y, x + y <= n and every colour j:  not (x, y, x+y all coloured j).
(x = y is included: S(k) here is the classical Schur number, S(3) = 13.)

vdW(k, L, n): every i gets at least one colour, and for every arithmetic
progression a, a+d, ..., a+(L-1)d inside 1..n (d >= 1) and every colour j:
not all of its terms coloured j.

Only "at least one colour" clauses are used.  This is sound for UNSAT
(a proper colouring would satisfy the CNF), and for SAT we decode a proper
colouring by taking the smallest true colour of each i (removing colours
never creates a monochromatic configuration).

Optional symmetry breaking (`sym=True`): the unit clause  v(1, 0).  This is
sound because permuting colour names maps good colourings to good
colourings, so if a good colouring exists, one with colour(1) = 0 exists.
"""

from __future__ import annotations


def var(i: int, j: int, k: int) -> int:
    return (i - 1) * k + j + 1


def alo_clauses(k: int, n: int) -> list[list[int]]:
    return [[var(i, j, k) for j in range(k)] for i in range(1, n + 1)]


def schur_cnf(k: int, n: int, sym: bool = False) -> list[list[int]]:
    cls = alo_clauses(k, n)
    for x in range(1, n + 1):
        for y in range(x, n + 1 - x):
            z = x + y
            for j in range(k):
                c = sorted({-var(x, j, k), -var(y, j, k), -var(z, j, k)})
                cls.append(c)
    if sym and n >= 1:
        cls.append([var(1, 0, k)])
    return cls


def vdw_cnf(k: int, L: int, n: int, sym: bool = False) -> list[list[int]]:
    assert L >= 2
    cls = alo_clauses(k, n)
    for a in range(1, n + 1):
        d = 1
        while a + (L - 1) * d <= n:
            for j in range(k):
                cls.append([-var(a + t * d, j, k) for t in range(L)])
            d += 1
    if sym and n >= 1:
        cls.append([var(1, 0, k)])
    return cls


def write_dimacs(cls: list[list[int]], nvars: int, path: str, comment: str = "") -> None:
    with open(path, "w") as fh:
        if comment:
            for line in comment.splitlines():
                fh.write(f"c {line}\n")
        fh.write(f"p cnf {nvars} {len(cls)}\n")
        for c in cls:
            fh.write(" ".join(map(str, c)) + " 0\n")


def decode(model: list[int], k: int, n: int) -> list[int]:
    pos = {l for l in model if l > 0}
    out = []
    for i in range(1, n + 1):
        cols = [j for j in range(k) if var(i, j, k) in pos]
        out.append(cols[0])
    return out


# ---- independent exact checkers (plain Python, no solver) ----

def check_schur(col: list[int], k: int) -> bool:
    """col[i-1] = colour of i.  True iff a proper Schur colouring of 1..len(col)."""
    n = len(col)
    if any(not (0 <= c < k) for c in col):
        return False
    for x in range(1, n + 1):
        for y in range(x, n + 1 - x):
            if col[x - 1] == col[y - 1] == col[x + y - 1]:
                return False
    return True


def check_vdw(col: list[int], k: int, L: int) -> bool:
    n = len(col)
    if any(not (0 <= c < k) for c in col):
        return False
    for a in range(1, n + 1):
        d = 1
        while a + (L - 1) * d <= n:
            if len({col[a + t * d - 1] for t in range(L)}) == 1:
                return False
            d += 1
    return True
