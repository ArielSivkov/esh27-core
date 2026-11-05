/-
EshLab.Targets.G050 -- small Schur and van der Waerden numbers (goal G050).
Mathlib-free; build alone with `lake build G050`.  See lab/experiments/G050/REPORT.md.

Kernel-checked (`decide +kernel`, axioms ⊆ {propext, Classical.choice, Quot.sound}):
  S(1)=1, S(2)=4, S(3)=13, W(2,3)=9, and lower bounds S(4)≥44, W(3,3)>26, W(2,4)>34.
Via CaDiCaL LRAT + core LRAT checker + `native_decide` (adds Lean.ofReduceBool):
  W(2,4)=35, W(3,3)=27 (and independent re-proofs of S(2), S(3), W(2,3) upper bounds).
-/
import EshLab.Targets.G050.Defs
import EshLab.Targets.G050.Search
import EshLab.Targets.G050.Witnesses
import EshLab.Targets.G050.Lower
import EshLab.Targets.G050.Upper
import EshLab.Targets.G050.LRAT
import EshLab.Targets.G050.UpperLRAT
