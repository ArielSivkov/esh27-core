import Hebrew.Theorems

namespace Hebrew
open Hebrew

/-! ## Equivalence with the Dershowitz–Reingold formulation -/

set_option maxHeartbeats 8000000 in
theorem dr_abstract (m : Nat) (l0 l1 l2 : Bool) (h01 : ¬ (l0 = true ∧ l1 = true))
    (h12 : ¬ (l1 = true ∧ l2 = true)) :
    let k0 := if l0 then 13 else 12
    let k1 := if l1 then 13 else 12
    let dd := fun (m : Nat) =>
      let day := 29 * m + (12084 + 13753 * m) / 25920
      if (3 * (day + 1)) % 7 < 3 then day + 1 else day
    let a := dd (m + k0)
    fixRH (31524 + (m + k0) * lunation) l1 l0 =
      (if dd (m + k0 + k1) - a = 356 then a + 2
       else if a - dd m = 382 then a + 1 else a) + 1 := by
  cases l0 <;> cases l1 <;> cases l2 <;> simp at h01 h12 <;> hebsimp <;>
    split <;> split <;> split <;> split <;> split <;> split <;> split <;> omega

/-- **Equivalence of formulations**: for every year y ≥ 2, the Rambam's procedure (7:1–6)
gives the same Rosh Hashana as the Dershowitz–Reingold formula used by the oracle
`hebrew_period.py` (ours = theirs + 1 by our choice of day 0). -/
theorem rambam_eq_dr (y : Nat) (hy : 2 ≤ y) : roshHashanah y = drNewYear y + 1 := by
  have e0 := elapsedMonths_eq_dr (y - 1) (by omega)
  have s0 := molad_succ (y - 1) (by omega)
  have s1 := molad_succ y (by omega)
  rw [show y - 1 + 1 = y by omega] at s0
  have hl := not_leap_and_leap_succ (y - 1)
  have hl' := not_leap_and_leap_succ y
  rw [show y - 1 + 1 = y by omega] at hl
  have key := dr_abstract (drElapsedMonths (y - 1)) (isLeap (y - 1)) (isLeap y) (isLeap (y + 1)) hl hl'
  have m1 : drElapsedMonths y = drElapsedMonths (y - 1) + (if isLeap (y - 1) then 13 else 12) := by
    rw [isLeap_eq_dr]; unfold drLeap drElapsedMonths
    split <;> rename_i h <;> simp only [decide_eq_true_eq] at h <;> omega
  have m2 : drElapsedMonths (y + 1) = drElapsedMonths y + (if isLeap y then 13 else 12) := by
    rw [isLeap_eq_dr]; unfold drLeap drElapsedMonths
    split <;> rename_i h <;> simp only [decide_eq_true_eq] at h <;> omega
  have mol : molad y = 31524 + drElapsedMonths y * lunation := by
    unfold molad; rw [elapsedMonths_eq_dr y (by omega)]
  unfold roshHashanah drNewYear drDelay1
  rw [mol, m2, m1]
  exact key

theorem rambam_eq_dr_one : roshHashanah 1 = drNewYear 1 + 1 := by decide

end Hebrew
