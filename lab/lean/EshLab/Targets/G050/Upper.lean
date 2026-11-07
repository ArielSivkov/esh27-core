/-
EshLab.Targets.G050.Upper -- upper bounds by a *verified exhaustive search*, checked by
the Lean kernel (`decide +kernel`).  No SAT solver, no `native_decide`.

`layer ok k n` lists every colour-list of length `n` passing the local test at every step
(no symmetry breaking).  `no_colouring_of_layer_nil` (proved in Search.lean) turns
`layer ok k n = []` into "no good colouring of {1,…,n}".
Axioms: ⊆ {propext, Classical.choice, Quot.sound}.
-/
import EshLab.Targets.G050.Lower

namespace EshLab.G050

set_option maxHeartbeats 0

theorem schur_upper_of_search {k n : Nat} (h : layer schurOk k n = []) :
    ∀ c : Nat → Fin k, ¬ SchurFree k n c :=
  fun c hc => no_colouring_of_layer_nil schurOk h c ((schurFree_iff c).1 hc)

theorem vdw_upper_of_search {k L n : Nat} (hL : 2 ≤ L) (h : layer (apOk L) k n = []) :
    ∀ c : Nat → Fin k, ¬ APFree k L n c :=
  fun c hc => no_colouring_of_layer_nil (apOk L) h c ((apFree_iff hL c).1 hc)

/-- Every 1-colouring of {1,2} has a monochromatic x + y = z. -/
theorem schur1_upper : ∀ c : Nat → Fin 1, ¬ SchurFree 1 2 c :=
  schur_upper_of_search (by decide +kernel)

/-- Every 2-colouring of {1,…,5} has a monochromatic x + y = z. -/
theorem schur2_upper : ∀ c : Nat → Fin 2, ¬ SchurFree 2 5 c :=
  schur_upper_of_search (by decide +kernel)

/-- Every 3-colouring of {1,…,14} has a monochromatic x + y = z. -/
theorem schur3_upper : ∀ c : Nat → Fin 3, ¬ SchurFree 3 14 c :=
  schur_upper_of_search (by decide +kernel)

/-- Every 2-colouring of {1,…,9} has a monochromatic 3-term AP. -/
theorem vdw2_3_upper : ∀ c : Nat → Fin 2, ¬ APFree 2 3 9 c :=
  vdw_upper_of_search (by decide) (by decide +kernel)

/-! ### Exact values (kernel-checked) -/

/-- **S(1) = 1.** -/
theorem schur_one : IsSchurNumber 1 1 := ⟨schur1_lower, schur1_upper⟩

/-- **S(2) = 4.** -/
theorem schur_two : IsSchurNumber 2 4 := ⟨schur2_lower, schur2_upper⟩

/-- **S(3) = 13.** -/
theorem schur_three : IsSchurNumber 3 13 := ⟨schur3_lower, schur3_upper⟩

/-- **W(2,3) = 9.** -/
theorem vdw_two_three : IsVdWNumber 2 3 9 := ⟨vdw2_3_lower, vdw2_3_upper⟩

end EshLab.G050
