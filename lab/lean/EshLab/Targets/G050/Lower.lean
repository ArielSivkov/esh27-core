/-
EshLab.Targets.G050.Lower -- lower bounds by explicit colourings.

Every theorem here is checked by the Lean kernel: the colouring is a concrete list
(Witnesses.lean, produced by CaDiCaL), and `decide +kernel` evaluates the Boolean
checker `allSteps`, whose meaning is fixed by the proved equivalences `schurFree_iff` /
`apFree_iff`.  Axioms: ⊆ {propext, Classical.choice, Quot.sound}; no `native_decide`.
-/
import EshLab.Targets.G050.Search
import EshLab.Targets.G050.Witnesses

namespace EshLab.G050

/-- Turn a kernel-checked run of the checker into `SchurFree`. -/
theorem schurFree_of_check {k n : Nat} (c : Nat → Fin k)
    (h : allSteps schurOk c n = true) : SchurFree k n c :=
  (schurFree_iff c).2 ((allSteps_iff _ c n).1 h)

theorem apFree_of_check {k L n : Nat} (hL : 2 ≤ L) (c : Nat → Fin k)
    (h : allSteps (apOk L) c n = true) : APFree k L n c :=
  (apFree_iff hL c).2 ((allSteps_iff _ c n).1 h)

/-- S(1) ≥ 1. -/
theorem schur1_lower : ∃ c : Nat → Fin 1, SchurFree 1 1 c :=
  ⟨ofList 1 (by decide) Witnesses.schur1_1, schurFree_of_check _ (by decide +kernel)⟩

/-- S(2) ≥ 4:  {1,4} | {2,3}. -/
theorem schur2_lower : ∃ c : Nat → Fin 2, SchurFree 2 4 c :=
  ⟨ofList 2 (by decide) Witnesses.schur2_4, schurFree_of_check _ (by decide +kernel)⟩

/-- S(3) ≥ 13. -/
theorem schur3_lower : ∃ c : Nat → Fin 3, SchurFree 3 13 c :=
  ⟨ofList 3 (by decide) Witnesses.schur3_13, schurFree_of_check _ (by decide +kernel)⟩

/-- S(4) ≥ 44. -/
theorem schur4_lower : ∃ c : Nat → Fin 4, SchurFree 4 44 c :=
  ⟨ofList 4 (by decide) Witnesses.schur4_44, schurFree_of_check _ (by decide +kernel)⟩

/-- W(2,3) > 8: a 2-colouring of {1,…,8} with no monochromatic 3-term AP. -/
theorem vdw2_3_lower : ∃ c : Nat → Fin 2, APFree 2 3 8 c :=
  ⟨ofList 2 (by decide) Witnesses.vdw2_3_8, apFree_of_check (by decide) _ (by decide +kernel)⟩

/-- W(3,3) > 26: a 3-colouring of {1,…,26} with no monochromatic 3-term AP. -/
theorem vdw3_3_lower : ∃ c : Nat → Fin 3, APFree 3 3 26 c :=
  ⟨ofList 3 (by decide) Witnesses.vdw3_3_26, apFree_of_check (by decide) _ (by decide +kernel)⟩

/-- W(2,4) > 34: a 2-colouring of {1,…,34} with no monochromatic 4-term AP. -/
theorem vdw2_4_lower : ∃ c : Nat → Fin 2, APFree 2 4 34 c :=
  ⟨ofList 2 (by decide) Witnesses.vdw2_4_34, apFree_of_check (by decide) _ (by decide +kernel)⟩

/-! Sanity checks against mis-formalization: the definitions do reject bad colourings. -/

/-- All-colour-0 on {1,2} is not Schur-free (1 + 1 = 2). -/
example : ¬ SchurFree 1 2 (fun _ => 0) := fun h => h 1 1 (by decide) (by decide) (by decide) ⟨rfl, rfl⟩

/-- The S(2) witness extended by colour 0 at 5 fails: 1 + 4 = 5 are all colour 0. -/
example : allSteps schurOk (ofList 2 (by decide) [0, 1, 1, 0, 0]) 5 = false := by decide +kernel

/-- …and by colour 1 at 5 fails too: 2 + 3 = 5. -/
example : allSteps schurOk (ofList 2 (by decide) [0, 1, 1, 0, 1]) 5 = false := by decide +kernel

/-- 1,2,3 all coloured 0 contains the 3-AP 1,2,3. -/
example : ¬ APFree 1 3 3 (fun _ => 0) :=
  fun h => h 1 1 (by decide) (by decide) (by decide) (fun _ _ => rfl)

end EshLab.G050
