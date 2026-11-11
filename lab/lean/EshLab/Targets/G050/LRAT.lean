/-
EshLab.Targets.G050.LRAT -- the SAT → Lean bridge.

* `schurCNF k n` / `vdwCNF k L n` : the CNF encodings, written *in Lean*, clause for clause in
  the same order as `lab/experiments/G050/encode.py` (so that an LRAT proof produced by
  CaDiCaL for the Python-written DIMACS file refers to the same clause numbers).
  CNF variable `k*(i-1) + j` (0-based; DIMACS variable `k*(i-1) + j + 1`) means
  "the integer `i` has colour `j`".
* `schurCNF_sat` / `vdwCNF_sat` : a good colouring gives a satisfying assignment
  (proved in Lean, so the Python encoder is NOT trusted).
* `Std.Tactic.BVDecide.LRAT.check` (core Lean's LRAT checker, proved sound in core as
  `LRAT.check_sound`) applied to an embedded certificate turns UNSAT of the CNF into
  "no good colouring".  The certificate itself is untrusted data: if it is wrong,
  `check` returns `false` and the proof fails to build.

How the `check … = true` side condition is discharged decides the trust level:
`decide +kernel` (kernel evaluation, axioms ⊆ {propext, Classical.choice, Quot.sound})
or `native_decide` (additionally trusts the compiler: axiom `Lean.ofReduceBool`).
-/
import EshLab.Targets.G050.Defs
import Std.Tactic.BVDecide.LRAT.Checker
import Std.Tactic.BVDecide.LRAT.Parser

namespace EshLab.G050

open Std.Sat Std.Tactic.BVDecide

/-- CNF variable for "integer `i` (≥ 1) has colour `j` (< k)". -/
def cvar (k i j : Nat) : Nat := k * (i - 1) + j

/-- At-least-one-colour clauses, for `i = 1, …, n`. -/
def aloCNF (k n : Nat) : CNF Nat :=
  (List.range n).map fun i₀ => (List.range k).map fun j => (cvar k (i₀ + 1) j, true)

/-- Schur clauses: for `x = 1, …, n`, `y = x, …, n - x`, colour `j`:
`¬x_j ∨ ¬y_j ∨ ¬(x+y)_j`. -/
def schurCNF (k n : Nat) : CNF Nat :=
  aloCNF k n ++
  (List.range n).flatMap fun x₀ =>
    (List.range (n + 1 - 2 * (x₀ + 1))).flatMap fun t =>
      (List.range k).map fun j =>
        [(cvar k (x₀ + 1) j, false), (cvar k (x₀ + 1 + t) j, false),
         (cvar k (x₀ + 1 + (x₀ + 1 + t)) j, false)]

/-- vdW clauses: for `a = 1, …, n`, `d = 1, …, (n - a)/(L - 1)`, colour `j`:
not all of `a, a+d, …, a+(L-1)d` have colour `j`. -/
def vdwCNF (k L n : Nat) : CNF Nat :=
  aloCNF k n ++
  (List.range n).flatMap fun a₀ =>
    (List.range ((n - (a₀ + 1)) / (L - 1))).flatMap fun d₀ =>
      (List.range k).map fun j =>
        (List.range L).map fun t => (cvar k (a₀ + 1 + t * (d₀ + 1)) j, false)

/-- The assignment induced by a colouring. -/
def asg (k : Nat) (c : Nat → Fin k) : Nat → Bool :=
  fun v => (c (v / k + 1)).val == v % k

theorem asg_cvar {k : Nat} (c : Nat → Fin k) {i j : Nat} (hi : 1 ≤ i) (hj : j < k) :
    asg k c (cvar k i j) = ((c i).val == j) := by
  have hk : 0 < k := by omega
  simp only [asg, cvar]
  rw [Nat.mul_add_div hk, Nat.mul_add_mod, Nat.div_eq_of_lt hj, Nat.mod_eq_of_lt hj]
  have : i - 1 + 0 + 1 = i := by omega
  rw [this]

theorem aloCNF_sat {k : Nat} (c : Nat → Fin k) (n : Nat) :
    CNF.eval (asg k c) (aloCNF k n) = true := by
  simp only [aloCNF, CNF.eval, CNF.Clause.eval, List.all_map, List.all_eq_true,
    List.mem_range, Function.comp_apply, List.any_map, List.any_eq_true]
  intro i₀ _
  refine ⟨(c (i₀ + 1)).val, (c (i₀ + 1)).isLt, ?_⟩
  rw [asg_cvar c (by omega) (c (i₀ + 1)).isLt]
  simp

theorem schurCNF_sat {k n : Nat} (c : Nat → Fin k) (h : SchurFree k n c) :
    CNF.eval (asg k c) (schurCNF k n) = true := by
  rw [schurCNF, CNF.eval_append, aloCNF_sat, Bool.true_and]
  simp only [CNF.eval, CNF.Clause.eval, List.all_eq_true, List.mem_flatMap, List.mem_map,
    List.mem_range]
  rintro cl ⟨x₀, hx, t, ht, j, hj, rfl⟩
  have hk : 0 < k := by omega
  have hxy := h (x₀ + 1) (x₀ + 1 + t) (by omega) (by omega) (by omega)
  rw [List.any_eq_true]
  by_cases h1 : (c (x₀ + 1)).val = j
  · by_cases h2 : (c (x₀ + 1 + t)).val = j
    · refine ⟨(cvar k (x₀ + 1 + (x₀ + 1 + t)) j, false), by simp, ?_⟩
      rw [asg_cvar c (by omega) hj]
      cases h3 : (c (x₀ + 1 + (x₀ + 1 + t))).val == j
      · rfl
      · exfalso
        apply hxy
        have h3' : (c (x₀ + 1 + (x₀ + 1 + t))).val = j := by simpa using h3
        exact ⟨Fin.ext (by omega), Fin.ext (by omega)⟩
    · refine ⟨(cvar k (x₀ + 1 + t) j, false), by simp, ?_⟩
      rw [asg_cvar c (by omega) hj]
      simp [h2]
  · refine ⟨(cvar k (x₀ + 1) j, false), by simp, ?_⟩
    rw [asg_cvar c (by omega) hj]
    simp [h1]

theorem vdwCNF_sat {k L n : Nat} (hL : 2 ≤ L) (c : Nat → Fin k) (h : APFree k L n c) :
    CNF.eval (asg k c) (vdwCNF k L n) = true := by
  rw [vdwCNF, CNF.eval_append, aloCNF_sat, Bool.true_and]
  simp only [CNF.eval, CNF.Clause.eval, List.all_eq_true, List.mem_flatMap, List.mem_map,
    List.mem_range]
  rintro cl ⟨a₀, ha, d₀, hd, j, hj, rfl⟩
  have hk : 0 < k := by omega
  -- the progression fits: a + (L-1) d ≤ n
  have hfit : a₀ + 1 + (L - 1) * (d₀ + 1) ≤ n := by
    have h1 : d₀ + 1 ≤ (n - (a₀ + 1)) / (L - 1) := hd
    have h2 := (Nat.le_div_iff_mul_le (by omega : 0 < L - 1)).1 h1
    rw [Nat.mul_comm] at h2
    omega
  have hap := h (a₀ + 1) (d₀ + 1) (by omega) (by omega) hfit
  rw [List.any_map, List.any_eq_true]
  apply Classical.byContradiction
  intro hne
  apply hap
  have hall : ∀ t, t < L → (c (a₀ + 1 + t * (d₀ + 1))).val = j := by
    intro t ht
    apply Classical.byContradiction
    intro hneq
    apply hne
    refine ⟨t, List.mem_range.2 ht, ?_⟩
    simp only [Function.comp_apply]
    rw [asg_cvar c (by omega) hj]
    simp [hneq]
  intro i hi
  have h0 := hall 0 (by omega)
  simp only [Nat.zero_mul, Nat.add_zero] at h0
  exact Fin.ext (by rw [hall i hi, h0])

/-! ### From a checked LRAT certificate to the mathematical statement -/

theorem schur_upper_of_lrat {k n : Nat} (prf : Array LRAT.IntAction)
    (hchk : LRAT.check prf (schurCNF k n) = true) : ∀ c : Nat → Fin k, ¬ SchurFree k n c := by
  intro c h
  have hunsat := LRAT.check_sound prf _ hchk
  have := hunsat (asg k c)
  rw [schurCNF_sat c h] at this
  exact Bool.noConfusion this

theorem vdw_upper_of_lrat {k L n : Nat} (hL : 2 ≤ L) (prf : Array LRAT.IntAction)
    (hchk : LRAT.check prf (vdwCNF k L n) = true) : ∀ c : Nat → Fin k, ¬ APFree k L n c := by
  intro c h
  have hunsat := LRAT.check_sound prf _ hchk
  have := hunsat (asg k c)
  rw [vdwCNF_sat hL c h] at this
  exact Bool.noConfusion this

/-- DIMACS rendering of a `CNF Nat` (variable `v` ↦ DIMACS `v + 1`), used only by the
sanity test that our Lean CNF is literally the file CaDiCaL saw (see `Certs`). -/
def toDimacsBody (f : CNF Nat) : String :=
  String.join <| f.map fun cl =>
    String.intercalate " " (cl.map fun (v, b) => if b then toString (v + 1) else "-" ++ toString (v + 1))
      ++ " 0\n"

end EshLab.G050

namespace EshLab.G050

open Std.Sat Std.Tactic.BVDecide

/-- Parse an ASCII/binary LRAT text (core Lean's parser) and run core Lean's checker.
The parser is untrusted (a wrong parse can only make `check` fail or check a different
proof of the same CNF); soundness rests on `LRAT.check_sound`. -/
def checkText (txt : String) (cnf : CNF Nat) : Bool :=
  match LRAT.parseLRATProof txt.toUTF8 with
  | .ok prf => LRAT.check prf cnf
  | .error _ => false

theorem schur_upper_of_text {k n : Nat} (txt : String)
    (hchk : checkText txt (schurCNF k n) = true) : ∀ c : Nat → Fin k, ¬ SchurFree k n c := by
  unfold checkText at hchk
  split at hchk
  · exact schur_upper_of_lrat _ hchk
  · exact absurd hchk Bool.false_ne_true

theorem vdw_upper_of_text {k L n : Nat} (hL : 2 ≤ L) (txt : String)
    (hchk : checkText txt (vdwCNF k L n) = true) : ∀ c : Nat → Fin k, ¬ APFree k L n c := by
  unfold checkText at hchk
  split at hchk
  · exact vdw_upper_of_lrat hL _ hchk
  · exact absurd hchk Bool.false_ne_true

end EshLab.G050
