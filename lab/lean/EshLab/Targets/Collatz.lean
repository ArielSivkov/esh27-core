/-
EshLab.Targets.Collatz -- STATEMENT ONLY (open problem, no proof attempted here).

Status: OPEN. Formalization level of the *statement*: reviewed-by-human = false
(see docs/architecture.md, "formalizing the wrong statement" is failure mode #1).
A proof of `CollatzConjecture` would be a world-class event; anything claiming
one must pass `lake build` with no `sorry`, no new `axiom`, and
`#print axioms` showing only [propext, Classical.choice, Quot.sound].
-/
import Mathlib

namespace EshLab.Targets

/-- One step of the Collatz map: `n ↦ n/2` if `n` is even, `3n+1` otherwise. -/
def collatzStep (n : ℕ) : ℕ :=
  if n % 2 = 0 then n / 2 else 3 * n + 1

/-- Collatz conjecture: every positive integer eventually reaches `1`
under iteration of `collatzStep`. -/
def CollatzConjecture : Prop :=
  ∀ n : ℕ, 0 < n → ∃ k : ℕ, collatzStep^[k] n = 1

/-- Sanity check of the encoding (guards against a mis-stated target):
3 → 10 → 5 → 16 → 8 → 4 → 2 → 1. -/
example : collatzStep^[7] 3 = 1 := by decide

/-- Sanity check: the trivial-cycle convention. -/
example : collatzStep 1 = 4 := by decide

end EshLab.Targets
