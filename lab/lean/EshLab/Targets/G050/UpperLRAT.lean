/-
EshLab.Targets.G050.UpperLRAT -- upper bounds via the SAT → Lean pipeline (CaDiCaL LRAT).

TRUST LEVEL — read this.  Each `checkText … = true` below is discharged by `native_decide`:
the LRAT check is *compiled and run*, and the result is admitted via the axiom
`Lean.ofReduceBool`.  This trusts the Lean compiler + runtime in addition to the kernel
(the same trust as the `bv_decide` tactic, which uses the same checker).  It is WEAKER than
the `decide +kernel` results in Lower.lean / Upper.lean.  We tried `decide +kernel` on the
LRAT checker itself: the kernel gets stuck (the checker's `Array`/well-founded code does not
reduce in the kernel), so this path needs `ofReduceBool` with core Lean 4.24.

What IS kernel-checked here: that the Lean-side CNF (`schurCNF`, `vdwCNF`) is satisfied by
every good colouring (`schurCNF_sat`, `vdwCNF_sat`), and that a successful `LRAT.check`
implies UNSAT (`LRAT.check_sound`, core Lean).  The Python encoder and CaDiCaL are NOT trusted.

`#print axioms` for these theorems lists `Lean.ofReduceBool` — see build log.
-/
import EshLab.Targets.G050.Lower
import EshLab.Targets.G050.LRAT
import EshLab.Targets.G050.Certs.Schur2
import EshLab.Targets.G050.Certs.Schur3
import EshLab.Targets.G050.Certs.VdW23
import EshLab.Targets.G050.Certs.VdW24
import EshLab.Targets.G050.Certs.VdW33

namespace EshLab.G050.ViaLRAT

open EshLab.G050

/-- Every 2-colouring of {1,…,5} has a monochromatic x + y = z  (LRAT, native). -/
theorem schur2_upper : ∀ c : Nat → Fin 2, ¬ SchurFree 2 5 c :=
  schur_upper_of_text Certs.schur2_5 (by native_decide)

/-- Every 3-colouring of {1,…,14} has a monochromatic x + y = z  (LRAT, native). -/
theorem schur3_upper : ∀ c : Nat → Fin 3, ¬ SchurFree 3 14 c :=
  schur_upper_of_text Certs.schur3_14 (by native_decide)

/-- Every 2-colouring of {1,…,9} has a monochromatic 3-AP  (LRAT, native). -/
theorem vdw2_3_upper : ∀ c : Nat → Fin 2, ¬ APFree 2 3 9 c :=
  vdw_upper_of_text (by decide) Certs.vdw2_3_9 (by native_decide)

/-- Every 2-colouring of {1,…,35} has a monochromatic 4-AP  (LRAT, native). -/
theorem vdw2_4_upper : ∀ c : Nat → Fin 2, ¬ APFree 2 4 35 c :=
  vdw_upper_of_text (by decide) Certs.vdw2_4_35 (by native_decide)

/-- Every 3-colouring of {1,…,27} has a monochromatic 3-AP  (LRAT, native). -/
theorem vdw3_3_upper : ∀ c : Nat → Fin 3, ¬ APFree 3 3 27 c :=
  vdw_upper_of_text (by decide) Certs.vdw3_3_27 (by native_decide)

/-- **W(2,4) = 35**  (lower bound kernel-checked; upper bound LRAT + `native_decide`). -/
theorem vdw_two_four : IsVdWNumber 2 4 35 := ⟨vdw2_4_lower, vdw2_4_upper⟩

/-- **W(3,3) = 27**  (lower bound kernel-checked; upper bound LRAT + `native_decide`). -/
theorem vdw_three_three : IsVdWNumber 3 3 27 := ⟨vdw3_3_lower, vdw3_3_upper⟩

end EshLab.G050.ViaLRAT
