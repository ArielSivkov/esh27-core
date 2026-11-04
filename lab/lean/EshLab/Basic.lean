/-
EshLab.Basic -- small, genuine, fully-proved warm-up theorems.

These exist to (1) smoke-test the toolchain / CI and (2) serve as style
examples for agents: explicit statements, short proofs, no `sorry`.
-/
import Mathlib

namespace EshLab

/-! ### Sum of the first `n` odd numbers -/

/-- `sumOdd n = 1 + 3 + 5 + ... + (2n - 1)`, defined by plain recursion (no `Finset`). -/
def sumOdd : Nat → Nat
  | 0 => 0
  | n + 1 => sumOdd n + (2 * n + 1)

/-- The sum of the first `n` odd numbers is `n^2`. -/
theorem sumOdd_eq_sq (n : Nat) : sumOdd n = n ^ 2 := by
  induction n with
  | zero => rfl
  | succ k ih =>
    show sumOdd k + (2 * k + 1) = (k + 1) ^ 2
    rw [ih]
    ring

/-! ### Gauss: `2 * (0 + 1 + ... + n) = n * (n + 1)` -/

/-- `sumTo n = 0 + 1 + ... + n`. -/
def sumTo : Nat → Nat
  | 0 => 0
  | n + 1 => sumTo n + (n + 1)

theorem two_mul_sumTo (n : Nat) : 2 * sumTo n = n * (n + 1) := by
  induction n with
  | zero => rfl
  | succ k ih =>
    show 2 * (sumTo k + (k + 1)) = (k + 1) * (k + 1 + 1)
    rw [Nat.left_distrib 2, ih]
    ring

/-! ### Infinitely many primes (via Mathlib) -/

/-- For every `n` there is a prime `p ≥ n`. -/
theorem exists_prime_ge (n : Nat) : ∃ p, n ≤ p ∧ p.Prime :=
  Nat.exists_infinite_primes n

/-- A kernel-checked computation: decided by evaluation, no tactic search. -/
theorem sumOdd_ten : sumOdd 10 = 100 := by decide

end EshLab
