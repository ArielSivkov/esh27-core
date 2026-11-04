/-
EshLab.Targets.Goldbach -- STATEMENT ONLY (open problem).
-/
import Mathlib

namespace EshLab.Targets

/-- Strong (binary) Goldbach conjecture: every even integer `n > 2`
is a sum of two primes. -/
def GoldbachConjecture : Prop :=
  ∀ n : ℕ, 2 < n → Even n → ∃ p q : ℕ, p.Prime ∧ q.Prime ∧ p + q = n

/-- Sanity check of the encoding on a small instance. -/
example : ∃ p q : ℕ, p.Prime ∧ q.Prime ∧ p + q = 10 :=
  ⟨3, 7, by norm_num, by norm_num, rfl⟩

end EshLab.Targets
