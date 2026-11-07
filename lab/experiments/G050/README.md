# G050 — Schur and van der Waerden numbers: SAT → Lean pipeline

Report (Hebrew): [REPORT.md](REPORT.md). Lean code: `lab/lean/EshLab/Targets/G050/`, built by the
standalone package `lab/lean/G050/`, which does not need Mathlib.

## Reproduce

```bash
cd lab/experiments/G050
pip install python-sat                 # used only to find witnesses (SAT side)
./setup_tools.sh                       # builds pinned CaDiCaL 3.0.1 + drat-trim/lrat-check into ./tools
python3 run_all.py                     # all instances (S(4) UNSAT takes about 3 min to solve and 7 min for DRAT check)
python3 run_all.py --skip-big          # skips the UNSAT proofs for S(4), W(3,3), W(2,4)
# regenerate the Lean certificate files (LRAT proof embedded as a String):
for x in "schur_k2_n5 schur2_5 Schur2" "schur_k3_n14 schur3_14 Schur3" "vdw_k2_L3_n9 vdw2_3_9 VdW23" \
         "vdw_k2_L4_n35 vdw2_4_35 VdW24" "vdw_k3_L3_n27 vdw3_3_27 VdW33"; do
  set -- $x; python3 lrat_to_lean.py proofs/$1.lrat $2 > ../../lean/EshLab/Targets/G050/Certs/$3.lean
done
cd ../../lean/G050 && lake build       # core Lean 4.24.0 only, about 1–2 min
```

## Files

| file | role |
|---|---|
| `encode.py` | DIMACS encoders `schur_cnf`, `vdw_cnf`, decoder, and independent exact checkers |
| `run_all.py` | finds witnesses (lower bounds), writes CNFs, runs CaDiCaL with DRAT and LRAT output, then drat-trim and lrat-check. Writes `results.json`, `witnesses.json` and `lean/.../Witnesses.lean` |
| `lrat_to_lean.py` | embeds an LRAT file in a Lean `String` (untrusted data) |
| `setup_tools.sh` | builds the pinned solver and checkers |
| `proofs/` | CNF, DRAT and LRAT files. Proofs are git-ignored and rebuilt by `run_all.py`. S(4): DRAT is 361 MB, LRAT is 606 MB |

## Encoding

Variable `(i-1)*k + j + 1` means "integer i has colour j". There are only at-least-one-colour
clauses, plus one negative clause per colour for each monochromatic pattern: x+y=z with
x ≤ y (Schur, x = y included), or an L-term AP (vdW). The CNFs used for the proofs have no
symmetry breaking (`--sym` adds the unit `v(1,0)`, but it is unused in the certified runs).
The Lean side defines the same CNF (`schurCNF`, `vdwCNF`) clause for clause and **proves**
that every good colouring satisfies it. So in the Lean results the Python encoder is not
trusted; only the clause *order* has to match, because LRAT refers to clause numbers.
