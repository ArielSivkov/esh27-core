"""Generate OEIS-format drafts + b-files from the verified outputs in ../out (no hand-copied numbers)."""
import os
OUT = '../out'; DR = '../drafts'
def rows(fn): return [list(map(int, l.split())) for l in open(os.path.join(OUT, fn)) if l.strip()]
def upto(seq, total=260):
    s = ''
    for i, x in enumerate(seq):
        t = (',' if s else '') + str(x)
        if len(s) + len(t) > total: return s, i
        s += t
    return s, len(seq)
def STU(seq):
    s, used = upto(seq)
    parts, cur = [], ''
    for x in s.split(','):
        t = (',' if cur else '') + x
        if len(cur) + len(t) > 88: parts.append(cur + ','); cur = x
        else: cur += t
    parts.append(cur)
    tags = ['%S', '%T', '%U']
    return '\n'.join(f'{tags[i]} A?????? {p}' for i, p in enumerate(parts[:3])), used
def bfile(name, seq, off):
    with open(os.path.join(DR, f'b_{name}.txt'), 'w') as f:
        for i, x in enumerate(seq): f.write(f'{i+off} {x}\n')

AUTH = '%A A?????? _Ariel Sivkov_, Nov 2026'
PY_A = open('oeis_programs.py').read().split('def T(')[0].split('\n', 2)[2].rstrip()
C_PROG = r'''(C)
#include <stdio.h>
#include <stdlib.h>
/* usage: prog k n  -> a(1..n); colours introduced in order of first use */
int k, n, col[200]; long long cnt[200];
void rec(int i, int used) {
  cnt[i-1]++;
  if (i > n) return;
  for (int c = 0; c < k && c <= used; c++) {
    int ok = 1;
    for (int x = 1; 2*x <= i; x++) if (col[x] == c && col[i-x] == c) { ok = 0; break; }
    if (ok) { col[i] = c; rec(i+1, c == used ? used+1 : used); col[i] = -1; }
  }
}
int main(int argc, char **argv) {
  k = atoi(argv[1]); n = atoi(argv[2]);
  for (int i = 0; i < 200; i++) col[i] = -1;
  rec(1, 0);
  for (int m = 1; m <= n; m++) printf("%d %lld\n", m, cnt[m]);
  return 0;
}'''
def o_lines(txt): return '\n'.join('%o A?????? ' + l for l in txt.split('\n'))

FS = ('H. Fredricksen and M. M. Sweet, <a href="https://doi.org/10.37236/1510">Symmetric Sum-Free Partitions and '
      'Lower Bounds for Schur Numbers</a>, Electron. J. Combin. 7 (2000), #R32.')
HEULE = ('Marijn J. H. Heule, <a href="https://arxiv.org/abs/1711.08076">Schur Number Five</a>, arXiv:1711.08076 [cs.LO], 2017; '
         'Proc. AAAI Conf. Artif. Intel. 32(1) (2018), 6598-6606.')

# ---------- k = 3, at most 3 blocks ----------
k3 = rows('canon_k3.txt'); A3 = [sum(r[1:]) for r in k3 if r[0] <= 13]
L3 = [3*r[1] + 6*r[2] + 6*r[3] for r in k3 if r[0] <= 13]
S, used = STU(A3); assert used == 13
open(os.path.join(DR, 'schur3_partitions.txt'), 'w').write(f'''{S}
%N A?????? Number of partitions of {{1,...,n}} into at most 3 sum-free sets (x + y = z with x = y allowed is forbidden within each set).
%C A?????? Equivalently, the number of 3-colorings of {{1,...,n}} with no monochromatic solution of x + y = z (x = y allowed), counted up to permutation of the colors.
%C A?????? A set S is sum-free if there are no x, y, z in S (x = y allowed) with x + y = z. Empty parts are not counted, so a partition with fewer than 3 nonempty parts is counted once.
%C A?????? The sequence is finite: a(n) = 0 for n > 13 = A045652(3) (Schur number S(3) = 13). a(13) = 3: there are exactly 3 sum-free partitions of {{1,...,13}} into 3 sets (Fredricksen and Sweet 2000, p. 5).
%C A?????? The number of labeled colorings (maps {{1,...,n}} -> {{1,2,3}}) is {", ".join(map(str, L3))} for n = 1..13; it equals 6*a(n) for n >= {min(i+1 for i in range(13) if all(L3[j]==6*A3[j] for j in range(i,13)))} (a 2-part partition can be colored in 3*2 = 6 ways, a 3-part one in 3! = 6 ways).
%C A?????? For n >= 5 every such partition has exactly 3 nonempty parts, so a(n) = T(n,3) of the triangle of partitions of {{1..n}} into exactly k sum-free sets (draft "schur_partition_triangle"); row sums of that triangle are A288817.
%D A?????? R. K. Guy, Unsolved Problems in Number Theory, 3rd ed., Springer, 2004, Section E11.
%H A?????? {FS}
%H A?????? {HEULE}
%e A?????? a(3) = 3: {{1,3}},{{2}}; {{1}},{{2,3}}; {{1}},{{2}},{{3}}.
%e A?????? a(4) = 5: {{1,4}},{{2,3}}; {{1,3}},{{2}},{{4}}; {{1,4}},{{2}},{{3}}; {{1}},{{2,3}},{{4}}; {{1}},{{2}},{{3,4}}.
%e A?????? a(13) = 3: {{1,4,7,10,13}},{{2,3,11,12}},{{5,6,8,9}}; {{1,4,10,13}},{{2,3,7,11,12}},{{5,6,8,9}}; {{1,4,10,13}},{{2,3,11,12}},{{5,6,7,8,9}} (they differ only in the set containing 7).
%o A?????? (Python)
{o_lines(PY_A)}
%o A?????? # a(n) = a_schur(n, 3), n = 1..13
{o_lines(C_PROG)}
%Y A?????? Cf. A045652, A030126, A288817, A007865, A072842, A297023.
%Y A?????? Cf. draft "schur4_partitions" (4 sets), draft "weak_schur3_partitions" (weak version), draft "schur_partition_triangle".
%K A?????? nonn,fini,full
%O A?????? 1,3
{AUTH}
''')

# ---------- k = 4 ----------
k4 = rows('canon_k4.txt'); A4 = [sum(r[1:]) for r in k4 if r[0] <= 44]
L4 = [4*r[1] + 12*r[2] + 24*r[3] + 24*r[4] for r in k4 if r[0] <= 44]
S, used = STU(A4)
bfile('schur4_partitions', A4, 1)
open(os.path.join(DR, 'schur4_partitions.txt'), 'w').write(f'''{S}
%N A?????? Number of partitions of {{1,...,n}} into at most 4 sum-free sets (x + y = z with x = y allowed is forbidden within each set).
%C A?????? Equivalently, the number of 4-colorings of {{1,...,n}} with no monochromatic solution of x + y = z (x = y allowed), counted up to permutation of the colors.
%C A?????? The sequence is finite with 44 terms: a(n) = 0 for n > 44 = A045652(4) (S(4) = 44, Baumert; see Golomb and Baumert 1965). The full sequence a(1..44) is in the b-file; the Data section shows a(1..{used}).
%C A?????? a(44) = 273 agrees with the count of 273 sum-free partitions of {{1,...,44}} into 4 sets reported by Fredricksen and Sweet (2000, p. 5) and by Heule (2017, "273 extreme certificates S(4,44) modulo symmetry").
%C A?????? The maximum is a(27) = {A4[26]}.
%C A?????? The number of labeled colorings (maps {{1,...,n}} -> {{1,2,3,4}}) equals 24*a(n) for n >= {min(i+1 for i in range(44) if all(L4[j]==24*A4[j] for j in range(i,44)))}; for n = 1..4 it is {", ".join(map(str, L4[:4]))}.
%C A?????? Computed by three independent programs that agree term by term: a canonical backtracker (colors in order of first use), a fully labeled bitmask backtracker (a(n) = labeled count / 24 for n >= 5), and SAT model enumeration with PySAT/CaDiCaL for n <= 12 and 39 <= n <= 45.
%H A?????? _Ariel Sivkov_, <a href="/A??????/b??????.txt">Table of n, a(n) for n = 1..44</a> (full sequence)
%H A?????? {FS}
%H A?????? Solomon W. Golomb and Leonard D. Baumert, <a href="https://doi.org/10.1145/321296.321300">Backtrack Programming</a>, J. ACM 12(4) (1965), 516-524.
%H A?????? {HEULE}
%e A?????? a(4) = 6: {{1,4}},{{2,3}}; {{1,3}},{{2}},{{4}}; {{1,4}},{{2}},{{3}}; {{1}},{{2,3}},{{4}}; {{1}},{{2}},{{3,4}}; {{1}},{{2}},{{3}},{{4}}.
%o A?????? (Python)
{o_lines(PY_A)}
%o A?????? # a(n) = a_schur(n, 4), n = 1..44 (slow in Python for n around 25; use the C program)
{o_lines(C_PROG)}
%Y A?????? Cf. A045652, A030126, A288817, A007865, A072842, A297023.
%Y A?????? Cf. draft "schur3_partitions" (3 sets), draft "schur_partition_triangle", draft "schur_extremal_count".
%K A?????? nonn,fini,full
%O A?????? 1,3
{AUTH}
''')

# ---------- weak k = 3 ----------
w3 = rows('canon_w3.txt'); W3 = [sum(r[1:]) for r in w3 if r[0] <= 23]
LW3 = [3*r[1] + 6*r[2] + 6*r[3] for r in w3 if r[0] <= 23]
S, used = STU(W3)
open(os.path.join(DR, 'weak_schur3_partitions.txt'), 'w').write(f'''{S}
%N A?????? Number of partitions of {{1,...,n}} into at most 3 weakly sum-free sets (no x + y = z with x, y, z distinct elements of the same set).
%C A?????? Equivalently, the number of 3-colorings of {{1,...,n}} with no monochromatic solution of x + y = z with x != y, counted up to permutation of the colors.
%C A?????? Here x + x = 2x within a set is allowed (weak Schur numbers); compare the draft "schur3_partitions" where it is forbidden.
%C A?????? The sequence is finite: a(n) = 0 for n > 23 = A072842(3) (weak Schur number WS(3) = 23). a(23) = 3 = A297023(3).
%C A?????? The number of labeled colorings (maps to {{1,2,3}}) is 6*a(n) for n >= {min(i+1 for i in range(23) if all(LW3[j]==6*W3[j] for j in range(i,23)))}; for n = 1..2 it is {", ".join(map(str, LW3[:2]))}.
%H A?????? Peter F. Blanchard, Frank Harary, and Rogério Reis, <a href="https://math.colgate.edu/~integers/g7/g7.Abstract.html">Partitions into sum-free sets</a>, Integers 6 (2006), Article A7.
%e A?????? a(2) = 2: {{1,2}} (1 + 1 = 2 is allowed here); {{1}},{{2}}.
%e A?????? a(3) = 4: {{1,2}},{{3}}; {{1,3}},{{2}}; {{1}},{{2,3}}; {{1}},{{2}},{{3}}. The single set {{1,2,3}} is excluded because 1 + 2 = 3.
%o A?????? (Python)
{o_lines(PY_A)}
%o A?????? # a(n) = a_schur(n, 3, weak=True), n = 1..23
%Y A?????? Cf. A072842, A297023, A118771, A045652, A288817.
%Y A?????? Cf. draft "schur3_partitions".
%K A?????? nonn,fini,full
%O A?????? 1,2
{AUTH}
''')

# ---------- terminal counts ----------
open(os.path.join(DR, 'schur_extremal_count.txt'), 'w').write(f'''%S A?????? 1,1,3,273
%N A?????? Number of partitions of {{1,...,S(n)}} into n sum-free sets, where S(n) = A045652(n) is the n-th Schur number.
%C A?????? A set is sum-free if it contains no x, y, z (x = y allowed) with x + y = z. Partitions are unordered (equivalently, n-colorings up to permutation of colors); for n >= 2 every such partition has n nonempty parts.
%C A?????? Analog of A297023 for (non-weak) Schur numbers.
%C A?????? a(3) = 3 and a(4) = 273 agree with Fredricksen and Sweet (2000, p. 5); a(4) = 273 is also stated by Heule (2017). a(5), the number of sum-free partitions of {{1,...,160}} into 5 sets, is not known to the author; Heule (2017) reports 334752 palindromic ones, Fredricksen and Sweet had conjectured 309408.
%H A?????? {FS}
%H A?????? {HEULE}
%e A?????? a(2) = 1: the only partition of {{1,2,3,4}} into 2 sum-free sets is {{1,4}},{{2,3}}.
%o A?????? (Python)
{o_lines(PY_A)}
%o A?????? # [a_schur(s, n) for n, s in [(1,1),(2,4),(3,13)]] gives [1, 1, 3]; a(4) = a_schur(44, 4) (C program recommended)
%Y A?????? Cf. A045652, A030126, A297023, A072842.
%K A?????? nonn,hard,more
%O A?????? 1,3
{AUTH}
''')

# ---------- triangle ----------
tri = rows('canon_all17.txt')
TT = [r[j] for r in tri for j in range(1, r[0] + 1)]
bfile('schur_partition_triangle', TT, 1)
S, used = STU(TT)
nrows = 0; c = 0
while c + nrows + 1 <= used: nrows += 1; c += nrows
S, _ = STU(TT[:c])
PY_T = open('oeis_programs.py').read().split('def T(')[1].split("if __name__")[0]
PY_T = 'def T(' + PY_T.rstrip()
open(os.path.join(DR, 'schur_partition_triangle.txt'), 'w').write(f'''{S}
%N A?????? Triangle read by rows: T(n,k) is the number of partitions of {{1,...,n}} into exactly k nonempty sum-free sets, 1 <= k <= n.
%C A?????? A set is sum-free if it contains no x, y, z (x = y allowed) with x + y = z.
%C A?????? Row sums are A288817(n).
%C A?????? T(n,k) = 0 for n > S(k) = A045652(k) (Schur's theorem). Column k = 3 is nonzero exactly for 3 <= n <= 13 and ends with T(13,3) = 3; column k = 4 is nonzero exactly for 4 <= n <= 44 and ends with T(44,4) = 273 (Fredricksen and Sweet 2000).
%C A?????? T(n,n) = 1; T(n,n-1) = floor((n-1)^2/2) = A007590(n-1) for n >= 2 (one 2-element part {{a,b}}, a < b, with b != 2a).
%C A?????? T(n,1) = 0 for n >= 2 and T(n,2) = 0 for n >= 5.
%H A?????? _Ariel Sivkov_, <a href="/A??????/b??????.txt">Table of n, a(n) for n = 1..{len(TT)}</a> (rows 1..{tri[-1][0]})
%H A?????? {FS}
%e A?????? Triangle begins:
''' + ''.join('%e A??????   ' + ' '.join(f'{x:>4}' for x in r[1:r[0]+1]) + '\n' for r in tri[:8]) + f'''%e A?????? T(4,2) = 1: {{1,4}},{{2,3}}. T(4,3) = 4: {{1,3}},{{2}},{{4}}; {{1,4}},{{2}},{{3}}; {{1}},{{2,3}},{{4}}; {{1}},{{2}},{{3,4}}.
%o A?????? (Python)
{o_lines(PY_T)}
%o A?????? # [T(n, k) for n in range(1, 11) for k in range(1, n+1)]
%Y A?????? Row sums: A288817. Cf. A045652, A030126, A007865, A007590, A008277.
%Y A?????? Cf. drafts "schur3_partitions" (column 3, n >= 5), "schur4_partitions".
%K A?????? nonn,tabl
%O A?????? 1,5
{AUTH}
''')
print('ok', len(A4), len(TT))
