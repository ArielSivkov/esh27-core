import Hebrew.Theorems

/-!
# Equivalence with the Dershowitz–Reingold formulation

`drNewYear` (Basic.lean) transcribes the oracle `hebrew_period.py`: the first two
dechiyot are folded into the "elapsed days" formula, and GaTRaD / BeTU'TaKPaT are
replaced by "a year may not have 356 days" / "may not have 382 days". We prove that
for every year `y ≥ 1` it gives the same Rosh Hashana as the Rambam's procedure
(`roshHashanah`, up to our day-numbering offset of 1). Method as in Theorems.lean:
reduce to the weekday index and time of the molad of the previous year, then a finite
case analysis closed by `omega`.
-/

namespace Hebrew

/-- The D–R delay (zaken folded into the day count, then lo ADU) from the molad's
weekday index `w` and time `h`. -/
def dr1 (w h : Nat) : Nat :=
  let z := if 19440 ≤ h then 1 else 0
  if (w + z) % 7 = 0 ∨ (w + z) % 7 = 3 ∨ (w + z) % 7 = 5 then z + 1 else z

theorem partsPerDay_le_molad (y : Nat) : partsPerDay ≤ molad y := by
  unfold molad; simp only [baharad, partsPerDay, partsPerHour]; omega

/-- `drDelay1` is "day of the molad − 1 + dr1". -/
theorem drDelay1_eq (y : Nat) (hy : 1 ≤ y) :
    drDelay1 y = molad y / partsPerDay - 1 + dr1 (molad y / partsPerDay % 7) (molad y % partsPerDay) := by
  have hm : molad y = 31524 + drElapsedMonths y * 765433 := by
    unfold molad; rw [elapsedMonths_eq_dr y hy]; rfl
  unfold drDelay1 dr1
  rw [hm]
  generalize drElapsedMonths y = m
  simp only [partsPerDay]
  (repeat' split) <;> omega

/-- Days and leftover parts of 12 / 13 lunations. -/
def kd (l : Bool) : Nat := if l then 383 else 354
def kr (l : Bool) : Nat := if l then 23269 else 9516

/-- Prune contradictory branches before splitting further, then finish. -/
macro "dr_check" : tactic => `(tactic|
  ((repeat' (first | (exfalso; omega) | split)) <;> simp <;> omega))

set_option maxHeartbeats 0 in
/-- The finite core: from the molad `(wm, hm)` of year y−1 and the leap flags `l0` of y−1
and `l1` of y, the Rambam's delay of year y equals the D–R delay plus the 356/382 correction. -/
theorem dr_abstract (wm hm : Nat) (hw : wm < 7) (hh : hm < 25920) (l0 l1 : Bool)
    (h01 : ¬ (l0 = true ∧ l1 = true)) :
    let c0 := if 25920 ≤ hm + kr l0 then 1 else 0
    let h := hm + kr l0 - 25920 * c0
    let w := (wm + kd l0 + c0) % 7
    let c1 := if 25920 ≤ h + kr l1 then 1 else 0
    let h1 := h + kr l1 - 25920 * c1
    let w1 := (w + kd l1 + c1) % 7
    delay w h l1 l0 =
      dr1 w h + (if (kd l1 + c1 + dr1 w1 h1) - dr1 w h = 356 then 2
                 else if (kd l0 + c0 + dr1 w h) - dr1 wm hm = 382 then 1 else 0) := by
  have h7 : wm = 0 ∨ wm = 1 ∨ wm = 2 ∨ wm = 3 ∨ wm = 4 ∨ wm = 5 ∨ wm = 6 := by omega
  cases l0 <;> cases l1 <;> simp at h01 <;>
    rcases h7 with rfl | rfl | rfl | rfl | rfl | rfl | rfl <;>
    simp only [kd, kr, dr1, delay, Bool.false_eq_true, Bool.true_eq_false, true_and, false_and,
      false_or, or_false, ↓reduceIte] <;> dr_check

/-- Division/modulus of a molad shifted by `k` days and `r < 25920` parts. -/
theorem shift_div_mod (t k r : Nat) (hr : r < 25920) :
    (t + (k * partsPerDay + r)) / partsPerDay = t / partsPerDay + k + (if 25920 ≤ t % partsPerDay + r then 1 else 0) ∧
    (t + (k * partsPerDay + r)) % partsPerDay = t % partsPerDay + r - 25920 * (if 25920 ≤ t % partsPerDay + r then 1 else 0) := by
  simp only [partsPerDay]; split <;> omega

theorem lunations_eq (l : Bool) : (if l then 13 else 12) * lunation = kd l * partsPerDay + kr l := by
  cases l <;> decide

/-- **Equivalence of formulations**: for every year y ≥ 2, the Rambam's procedure (7:1–6)
gives the same Rosh Hashana as the Dershowitz–Reingold formula of the oracle
`hebrew_period.py` (ours = theirs + 1 by our choice of day 0). -/
theorem rambam_eq_dr (y : Nat) (hy : 2 ≤ y) : roshHashanah y = drNewYear y + 1 := by
  have hl01 := not_leap_and_leap_succ (y - 1)
  have hl12 := not_leap_and_leap_succ y
  rw [show y - 1 + 1 = y by omega] at hl01
  have s0 := molad_succ (y - 1) (by omega)
  rw [show y - 1 + 1 = y by omega] at s0
  have s1 := molad_succ y (by omega)
  have ht := partsPerDay_le_molad (y - 1)
  unfold roshHashanah drNewYear
  rw [fixRH_eq_delay, drDelay1_eq y (by omega), drDelay1_eq (y + 1) (by omega),
    drDelay1_eq (y - 1) (by omega), s1, s0, lunations_eq, lunations_eq]
  generalize molad (y - 1) = t at ht
  generalize isLeap (y - 1) = l0 at hl01
  generalize isLeap y = l1 at hl01 hl12
  have hr0 : kr l0 < 25920 := by cases l0 <;> decide
  have hr1 : kr l1 < 25920 := by cases l1 <;> decide
  rw [(shift_div_mod t _ _ hr0).1, (shift_div_mod t _ _ hr0).2]
  rw [← Nat.add_assoc, (shift_div_mod _ _ _ hr1).1, (shift_div_mod _ _ _ hr1).2]
  rw [(shift_div_mod t _ _ hr0).1, (shift_div_mod t _ _ hr0).2]
  have key := dr_abstract (t / partsPerDay % 7) (t % partsPerDay) (Nat.mod_lt _ (by decide))
    (Nat.mod_lt _ (by decide)) l0 l1 hl01
  simp only [] at key
  have e1 : ∀ k c, (t / partsPerDay + k + c) % 7 = (t / partsPerDay % 7 + k + c) % 7 := by
    intro k c; omega
  have e2 : ∀ k c k' c', (t / partsPerDay + k + c + k' + c') % 7 =
      ((t / partsPerDay % 7 + k + c) % 7 + k' + c') % 7 := by intro k c k' c'; omega
  rw [e1, e2, key]
  have hD : 1 ≤ t / partsPerDay := by simp only [partsPerDay] at ht ⊢; omega
  split <;> split <;> omega

theorem rambam_eq_dr_one : roshHashanah 1 = drNewYear 1 + 1 := by decide

/-- For every year y ≥ 1 the two formulations agree. -/
theorem rambam_eq_dr' (y : Nat) (hy : 1 ≤ y) : roshHashanah y = drNewYear y + 1 := by
  rcases Nat.lt_or_ge y 2 with h | h
  · have : y = 1 := by omega
    subst this; exact rambam_eq_dr_one
  · exact rambam_eq_dr y h

end Hebrew
