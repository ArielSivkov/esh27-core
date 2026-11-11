import Hebrew.Basic

/-!
# Theorems on the Rambam's fixed calendar

Method: every "for all years" statement is reduced to a lemma about an *arbitrary*
molad `t : Nat` and arbitrary leap flags (the `fixRH`-level lemmas below), which is
then closed by case splits on the `if`s of the dechiyot and `omega` (Presburger
arithmetic with `/` and `%` by literals). Concrete facts (witness years) are closed
by the kernel with `decide`. No `native_decide`, no `sorry`, no extra axioms.
-/

namespace Hebrew

/-- Unfold the calendar abbreviations so that `omega` sees literals. -/
macro "hebsimp" : tactic => `(tactic| simp only [fixRH, partsPerDay, partsPerHour, lunation,
  isADU, moladZaken, gatrad, betutakpat, weekday, Bool.false_eq_true, true_and, false_and,
  and_false, and_true, or_false, false_or, reduceCtorEq] at *)

/-! ## Arithmetic of months and leap years -/

theorem monthsBeforeInCycle_eq : ∀ r, r < 19 → monthsBeforeInCycle r = (235 * r + 1) / 19 := by
  decide

/-- The Rambam's cycle-and-remainder count (6:14) equals the closed form ⌊(235y−234)/19⌋. -/
theorem elapsedMonths_eq_dr (y : Nat) (hy : 1 ≤ y) : elapsedMonths y = drElapsedMonths y := by
  unfold elapsedMonths drElapsedMonths
  rw [monthsBeforeInCycle_eq _ (Nat.mod_lt _ (by decide))]
  omega

theorem leapCycleYear_eq : ∀ r, r < 19 → leapCycleYear (r + 1) = decide ((7 * r + 8) % 19 < 7) := by
  decide

/-- גו"ח י"א י"ד י"ז י"ט (6:11) equals the arithmetic test `(7y+1) mod 19 < 7`. -/
theorem isLeap_eq_dr (y : Nat) : isLeap y = drLeap y := by
  unfold isLeap cycleYear drLeap
  rw [leapCycleYear_eq _ (Nat.mod_lt _ (by decide))]
  have : (7 * ((y + 18) % 19) + 8) % 19 = (7 * y + 1) % 19 := by omega
  rw [this]

/-- Two consecutive years are never both leap years. -/
theorem not_leap_and_leap_succ (y : Nat) : ¬ (isLeap y = true ∧ isLeap (y + 1) = true) := by
  simp only [isLeap_eq_dr, drLeap, decide_eq_true_eq]
  rw [show 7 * (y + 1) + 1 = (7 * y + 1) + 7 by omega, Nat.add_mod (7 * y + 1) 7 19]
  have := Nat.mod_lt (7 * y + 1) (show 19 > 0 by decide)
  generalize (7 * y + 1) % 19 = r at *
  revert this; revert r; decide

theorem monthsBeforeInCycle_succ : ∀ r, r < 18 →
    monthsBeforeInCycle (r + 1) = monthsBeforeInCycle r + (if leapCycleYear (r + 1) then 13 else 12) := by
  decide

/-- Elapsed months grow by 12 or 13 per year (6:10–11, 6:14). -/
theorem elapsedMonths_succ (y : Nat) (hy : 1 ≤ y) :
    elapsedMonths (y + 1) = elapsedMonths y + (if isLeap y then 13 else 12) := by
  unfold elapsedMonths isLeap cycleYear
  rw [show (y + 18) % 19 = (y - 1) % 19 by omega, show y + 1 - 1 = y by omega]
  by_cases h : (y - 1) % 19 = 18
  · rw [show y / 19 = (y - 1) / 19 + 1 by omega, show y % 19 = 0 by omega, h,
      show monthsBeforeInCycle 0 = 0 from rfl, show monthsBeforeInCycle 18 = 222 from rfl,
      show leapCycleYear 19 = true from rfl]
    simp only [↓reduceIte]; omega
  · have hr : (y - 1) % 19 < 18 := by have := Nat.mod_lt (y - 1) (show 19 > 0 by decide); omega
    rw [show y / 19 = (y - 1) / 19 by omega, show y % 19 = (y - 1) % 19 + 1 by omega,
      monthsBeforeInCycle_succ _ hr]
    omega

theorem elapsedMonths_add_cycles (y c : Nat) (hy : 1 ≤ y) :
    elapsedMonths (y + 19 * c) = elapsedMonths y + 235 * c := by
  unfold elapsedMonths
  rw [show (y + 19 * c - 1) / 19 = (y - 1) / 19 + c by omega,
    show (y + 19 * c - 1) % 19 = (y - 1) % 19 by omega]
  omega

/-- "וְתוֹסִיף שְׁאֵרִיתָהּ … אִם פְּשׁוּטָה הִיא שְׁאֵרִית הַפְּשׁוּטָה וְאִם מְעֻבֶּרֶת הִיא שְׁאֵרִית
הַמְעֻבֶּרֶת. יֵצֵא לְךָ מוֹלַד שָׁנָה שֶׁלְּאַחֲרֶיהָ" — "add its remainder — of an ordinary year or of
a leap year … you will determine the conjunction of the following year" (6:8):
molad(y+1) = molad(y) + 12 or 13 lunations. -/
theorem molad_succ (y : Nat) (hy : 1 ≤ y) :
    molad (y + 1) = molad y + (if isLeap y then 13 else 12) * lunation := by
  unfold molad
  rw [elapsedMonths_succ y hy]; split <;> simp only [lunation] <;> omega

/-- 6:12–13: a 19-year cycle advances the molad by 235 lunations (בי"ו תקצ"ה mod 7). -/
theorem molad_add_cycle (y : Nat) (hy : 1 ≤ y) : molad (y + 19) = molad y + 235 * lunation := by
  unfold molad
  rw [show y + 19 = y + 19 * 1 by rfl, elapsedMonths_add_cycles y 1 hy]; simp only [lunation]; omega

theorem cycle_remainder : (235 * lunation) % partsPerWeek = 2 * partsPerDay + 16 * partsPerHour + 595 := by
  decide

/-! ## Reduction to the molad's weekday and time

`fixRH t` depends on `t` only through its day `t / 25920` and its time `t % 25920`, and
the dechiyot only through the weekday `t / 25920 % 7`. We factor the delay (0, 1 or 2
days) out as `delay w h`, and the keviyah of a year as `kevOf w h`, a function of the
weekday index `w < 7` and time `h < 25920` of the molad plus three leap flags. The
"for all years" theorems then follow from a statement over `w < 7` (7 cases) and
`h` (linear inequalities, `omega`). -/

/-- Delay of Rosh Hashana after the molad day, from the molad's weekday index
`w = d % 7` (0 = Sunday) and time `h` (parts from nightfall): the four dechiyot of 7:1–6. -/
def delay (w h : Nat) (leap prevLeap : Bool) : Nat :=
  let d1 := if 18 * 1080 ≤ h ∨ (leap = false ∧ w = 2 ∧ 9 * 1080 + 204 ≤ h) ∨
               (prevLeap = true ∧ w = 1 ∧ 15 * 1080 + 589 ≤ h) then 1 else 0
  if (w + d1) % 7 = 0 ∨ (w + d1) % 7 = 3 ∨ (w + d1) % 7 = 5 then d1 + 1 else d1

theorem fixRH_eq_delay (t : Nat) (l p : Bool) :
    fixRH t l p = t / partsPerDay + delay (t / partsPerDay % 7) (t % partsPerDay) l p := by
  cases l <;> cases p <;> hebsimp <;> unfold delay <;>
    simp only [Bool.false_eq_true, Bool.true_eq_false, true_and, false_and, or_false, false_or] <;>
    (repeat' split) <;> omega

/-- 7:3: Rosh Hashana is the day of the molad, or at most "בִּשְׁלִישִׁי מִיּוֹם הַמּוֹלָד". -/
theorem delay_le (w h : Nat) (l p : Bool) : delay w h l p ≤ 2 := by
  simp only [delay]; (repeat' split) <;> omega

theorem fixRH_bounds (t : Nat) (l p : Bool) :
    t / partsPerDay ≤ fixRH t l p ∧ fixRH t l p ≤ t / partsPerDay + 2 := by
  rw [fixRH_eq_delay]; have := delay_le (t / partsPerDay % 7) (t % partsPerDay) l p; omega

theorem delay_not_adu (w h : Nat) (l p : Bool) (hw : w < 7) :
    (w + delay w h l p) % 7 ≠ 0 ∧ (w + delay w h l p) % 7 ≠ 3 ∧ (w + delay w h l p) % 7 ≠ 5 := by
  simp only [delay]; (repeat' split) <;> omega

theorem fixRH_not_adu (t : Nat) (l p : Bool) : ¬ isADU (fixRH t l p) := by
  rw [fixRH_eq_delay]
  have := delay_not_adu (t / partsPerDay % 7) (t % partsPerDay) l p (Nat.mod_lt _ (by decide))
  simp only [isADU, weekday]; omega

/-- Shifting the molad by whole weeks shifts Rosh Hashana by the same number of days. -/
theorem fixRH_add_weeks (t c : Nat) (l p : Bool) :
    fixRH (t + partsPerWeek * c) l p = fixRH t l p + 7 * c := by
  rw [fixRH_eq_delay, fixRH_eq_delay]
  have h1 : (t + partsPerWeek * c) / partsPerDay = t / partsPerDay + 7 * c := by
    simp only [partsPerWeek, partsPerDay]; omega
  have h2 : (t + partsPerWeek * c) % partsPerDay = t % partsPerDay := by
    simp only [partsPerWeek, partsPerDay]; omega
  have h3 : (t / partsPerDay + 7 * c) % 7 = t / partsPerDay % 7 := by omega
  rw [h1, h2, h3]; omega

/-- 12 lunations = 354 d 8 h 876 p; 13 lunations = 383 d 21 h 589 p (6:4). -/
theorem twelve_lunations : 12 * lunation = 354 * partsPerDay + 9516 := by decide
theorem thirteen_lunations : 13 * lunation = 383 * partsPerDay + 23269 := by decide

/-- The keviyah determined by the molad's weekday `w`, time `h`, the leap flags of this
year (`l`), the previous (`pl`) and the next (`nl`) year. -/
def kevOf (w h : Nat) (l pl nl : Bool) : Nat × Nat :=
  let a := delay w h l pl
  let k := if l then 383 else 354
  let r := if l then 23269 else 9516
  let c := if 25920 ≤ h + r then 1 else 0
  let b := delay ((w + k + c) % 7) (h + r - 25920 * c) nl l
  ((w + a) % 7 + 1, k + c + b - a)

theorem keviyah_eq_kevOf (y : Nat) (hy : 1 ≤ y) :
    keviyah y = kevOf (molad y / partsPerDay % 7) (molad y % partsPerDay)
      (isLeap y) (isLeap (y - 1)) (isLeap (y + 1)) := by
  unfold keviyah yearLength roshHashanah
  rw [molad_succ y hy, show y + 1 - 1 = y by omega, fixRH_eq_delay, fixRH_eq_delay]
  unfold kevOf
  generalize molad y = t
  cases isLeap y <;> simp only [Bool.false_eq_true, ↓reduceIte, twelve_lunations, thirteen_lunations] <;>
  · have hc : ∀ k r, r < 25920 → (t + (k * partsPerDay + r)) / partsPerDay = t / partsPerDay + k + (if 25920 ≤ t % partsPerDay + r then 1 else 0) ∧
        (t + (k * partsPerDay + r)) % partsPerDay = t % partsPerDay + r - 25920 * (if 25920 ≤ t % partsPerDay + r then 1 else 0) := by
      intro k r hr; simp only [partsPerDay]; split <;> omega
    rw [(hc _ _ (by decide)).1, (hc _ _ (by decide)).2]
    have hm : ∀ k c, (t / partsPerDay + k + c) % 7 = (t / partsPerDay % 7 + k + c) % 7 := by intro k c; omega
    rw [hm]
    simp only [weekday, Prod.mk.injEq]
    constructor
    · omega
    · have := delay_le (t / partsPerDay % 7) (t % partsPerDay)
      split <;> omega

/-- Tactic for the finite check: unfold, split every `if`, normalize literals, and let
`omega` close the contradictory branches. -/
macro "kev_check" : tactic => `(tactic|
  (simp only [kevOf, delay, keviyotCommon, keviyotLeap, List.mem_cons, List.not_mem_nil,
     Prod.mk.injEq, or_false, Bool.false_eq_true, Bool.true_eq_false, true_and, false_and,
     and_false, and_true, false_or, true_or, or_true, ↓reduceIte]
   <;> (repeat' split) <;> simp <;> omega))

set_option maxHeartbeats 0 in
/-- Over the 7 weekdays and all times: a common year (any neighbours) has one of the
7 common keviyot. -/
theorem kevOf_common_mem (w h : Nat) (hw : w < 7) (hh : h < 25920) (pl nl : Bool) :
    kevOf w h false pl nl ∈ keviyotCommon := by
  have h7 : w = 0 ∨ w = 1 ∨ w = 2 ∨ w = 3 ∨ w = 4 ∨ w = 5 ∨ w = 6 := by omega
  cases pl <;> cases nl <;> rcases h7 with rfl | rfl | rfl | rfl | rfl | rfl | rfl <;> kev_check

set_option maxHeartbeats 0 in
/-- A leap year (followed, necessarily, by a common year) has one of the 7 leap keviyot. -/
theorem kevOf_leap_mem (w h : Nat) (hw : w < 7) (hh : h < 25920) (pl : Bool) :
    kevOf w h true pl false ∈ keviyotLeap := by
  have h7 : w = 0 ∨ w = 1 ∨ w = 2 ∨ w = 3 ∨ w = 4 ∨ w = 5 ∨ w = 6 := by omega
  cases pl <;> rcases h7 with rfl | rfl | rfl | rfl | rfl | rfl | rfl <;> kev_check

/-! ## Main theorems -/

/-- **(a) Lo ADU** (7:1): "אֵין קוֹבְעִין לְעוֹלָם רֹאשׁ חֹדֶשׁ תִּשְׁרֵי … לֹא בְּאֶחָד בְּשַׁבָּת וְלֹא
בִּרְבִיעִי בְּשַׁבָּת וְלֹא בְּעֶרֶב שַׁבָּת" — Rosh Hashana of every year falls neither on Sunday
(1), Wednesday (4) nor Friday (6). (True by construction of the procedure; stated for
every `y : Nat`.) -/
theorem lo_adu (y : Nat) :
    weekday (roshHashanah y) ≠ 1 ∧ weekday (roshHashanah y) ≠ 4 ∧ weekday (roshHashanah y) ≠ 6 := by
  have := fixRH_not_adu (molad y) (isLeap y) (isLeap (y - 1))
  unfold roshHashanah; simp only [isADU] at this; omega

/-- Rosh Hashana is on Monday, Tuesday, Thursday or Shabbat (the "בּ ג ה ז" of 7:7). -/
theorem rh_weekday (y : Nat) :
    weekday (roshHashanah y) = 2 ∨ weekday (roshHashanah y) = 3 ∨
    weekday (roshHashanah y) = 5 ∨ weekday (roshHashanah y) = 7 := by
  have := lo_adu y; simp only [weekday] at *; omega

/-- The keviyah of a common year is one of `keviyotCommon`, of a leap year one of
`keviyotLeap`. -/
theorem keviyah_mem (y : Nat) (hy : 1 ≤ y) :
    (isLeap y = false → keviyah y ∈ keviyotCommon) ∧ (isLeap y = true → keviyah y ∈ keviyotLeap) := by
  rw [keviyah_eq_kevOf y hy]
  have hw : molad y / partsPerDay % 7 < 7 := Nat.mod_lt _ (by decide)
  have hh : molad y % partsPerDay < 25920 := Nat.mod_lt _ (by decide)
  cases hl : isLeap y
  · constructor
    · intro _; exact kevOf_common_mem _ _ hw hh _ _
    · intro h; cases h
  · have hn : isLeap (y + 1) = false := by
      have := not_leap_and_leap_succ y; cases h : isLeap (y + 1) <;> simp_all
    rw [hn]; constructor
    · intro h; cases h
    · intro _; exact kevOf_leap_mem _ _ hw hh _

/-- **(c₁) At most 14 keviyot**: every year's keviyah is one of the 14 listed. -/
theorem keviyah_mem_keviyot14 (y : Nat) (hy : 1 ≤ y) : keviyah y ∈ keviyot14 := by
  have := keviyah_mem y hy
  unfold keviyot14; rw [List.mem_append]
  cases hl : isLeap y <;> simp_all

/-- The keviyah of year `y ≥ 1`, spelled out: leap flag, weekday of Rosh Hashana, length. -/
theorem keviyah_cases (y : Nat) (hy : 1 ≤ y) :
    (isLeap y = false ∧
      ((weekday (roshHashanah y) = 2 ∧ yearLength y = 353) ∨ (weekday (roshHashanah y) = 2 ∧ yearLength y = 355) ∨
       (weekday (roshHashanah y) = 3 ∧ yearLength y = 354) ∨ (weekday (roshHashanah y) = 5 ∧ yearLength y = 354) ∨
       (weekday (roshHashanah y) = 5 ∧ yearLength y = 355) ∨ (weekday (roshHashanah y) = 7 ∧ yearLength y = 353) ∨
       (weekday (roshHashanah y) = 7 ∧ yearLength y = 355))) ∨
    (isLeap y = true ∧
      ((weekday (roshHashanah y) = 2 ∧ yearLength y = 383) ∨ (weekday (roshHashanah y) = 2 ∧ yearLength y = 385) ∨
       (weekday (roshHashanah y) = 3 ∧ yearLength y = 384) ∨ (weekday (roshHashanah y) = 5 ∧ yearLength y = 383) ∨
       (weekday (roshHashanah y) = 5 ∧ yearLength y = 385) ∨ (weekday (roshHashanah y) = 7 ∧ yearLength y = 383) ∨
       (weekday (roshHashanah y) = 7 ∧ yearLength y = 385))) := by
  have := keviyah_mem y hy
  simp only [keviyah, keviyotCommon, keviyotLeap, List.mem_cons, List.not_mem_nil, Prod.mk.injEq,
    or_false] at this
  cases hl : isLeap y <;> simp_all

/-- Common years have 353–355 days, leap years 383–385 (in both directions). -/
theorem yearLength_leap_iff (y : Nat) (hy : 1 ≤ y) :
    (isLeap y = false ↔ yearLength y = 353 ∨ yearLength y = 354 ∨ yearLength y = 355) ∧
    (isLeap y = true ↔ yearLength y = 383 ∨ yearLength y = 384 ∨ yearLength y = 385) := by
  have := keviyah_cases y hy
  cases hl : isLeap y <;> simp_all <;> omega

/-- **(b) Legal year lengths** (cf. Russinoff's ACL2 `legal-year-lengths`): a common year
has 353, 354 or 355 days and a leap year 383, 384 or 385 — the "חסרה / כסדרה / שלמה" of
8:6–8 ("אִם תִּמְצָא בֵּינֵיהֶן שְׁנֵי יָמִים … שְׁלֹשָׁה … אַרְבָּעָה"). -/
theorem yearLength_legal (y : Nat) (hy : 1 ≤ y) :
    (isLeap y = false → yearLength y = 353 ∨ yearLength y = 354 ∨ yearLength y = 355) ∧
    (isLeap y = true → yearLength y = 383 ∨ yearLength y = 384 ∨ yearLength y = 385) :=
  ⟨(yearLength_leap_iff y hy).1.mp, (yearLength_leap_iff y hy).2.mp⟩

/-- (b') Year lengths lie in {353, 354, 355, 383, 384, 385}. -/
theorem yearLength_mem (y : Nat) (hy : 1 ≤ y) :
    yearLength y ∈ [353, 354, 355, 383, 384, 385] := by
  have := keviyah_cases y hy
  simp only [List.mem_cons, List.not_mem_nil]; omega

/-- **Rambam 8:10, formalized**: "כָּל שָׁנָה שֶׁיִּהְיֶה רֹאשׁ הַשָּׁנָה בָּהּ בַּשְּׁלִישִׁי תִּהְיֶה
לְעוֹלָם כְּסִדְרָן … בֵּין פְּשׁוּטָה בֵּין מְעֻבֶּרֶת. וְאִם יִהְיֶה רֹאשׁ הַשָּׁנָה בְּשַׁבָּת אוֹ בְּשֵׁנִי לֹא
תִּהְיֶה כְּסִדְרָן לְעוֹלָם … וְאִם יִהְיֶה רֹאשׁ הַשָּׁנָה בַּחֲמִישִׁי. אִם פְּשׁוּטָה הִיא אִי אֶפְשָׁר
שֶׁיִּהְיוּ חֳדָשֶׁיהָ חֲסֵרִים … וְאִם מְעֻבֶּרֶת הִיא אִי אֶפְשָׁר שֶׁיִּהְיוּ חֳדָשֶׁיהָ כְּסִדְרָן" —
"Whenever Rosh HaShanah is on a Tuesday, the year will [proceed] in order … whether
ordinary or leap. Whenever … on the Sabbath or on a Monday, the year will never
[proceed] in order … On a Thursday: if ordinary, its months cannot be lacking; if leap,
its months cannot proceed in order." (`yearKind` 0 = חסרה, 1 = כסדרה, 2 = שלמה.)
Cf. Russinoff's ACL2 `keviyot`. -/
theorem rambam_8_10 (y : Nat) (hy : 1 ≤ y) :
    (weekday (roshHashanah y) = 3 → yearKind y = 1) ∧
    (weekday (roshHashanah y) = 7 ∨ weekday (roshHashanah y) = 2 → yearKind y ≠ 1) ∧
    (weekday (roshHashanah y) = 5 → isLeap y = false → yearKind y ≠ 0) ∧
    (weekday (roshHashanah y) = 5 → isLeap y = true → yearKind y ≠ 1) := by
  have := keviyah_cases y hy
  unfold yearKind
  cases hl : isLeap y <;> simp_all <;> omega

theorem keviyot14_length : keviyot14.length = 14 := rfl

theorem keviyot14_nodup : keviyot14.Nodup := by decide

/-- Witness years, one per keviyah (checked by the kernel). -/
theorem keviyot_witnesses :
    [15, 1, 4, 7, 23, 26, 2, 8, 14, 27, 3, 6, 19, 25].map keviyah = keviyot14 := by
  decide

/-- **(c₂) Each of the 14 keviyot occurs.** -/
theorem keviyot14_occur (k : Nat × Nat) (hk : k ∈ keviyot14) : ∃ y, 1 ≤ y ∧ keviyah y = k := by
  rw [← keviyot_witnesses] at hk
  obtain ⟨y, hy, rfl⟩ := List.mem_map.mp hk
  refine ⟨y, ?_, rfl⟩
  simp only [List.mem_cons, List.not_mem_nil, or_false] at hy
  omega

/-- **(c) Exactly 14 keviyot**: the set of keviyot of years ≥ 1 is `keviyot14`, a list of 14
distinct pairs. -/
theorem exactly_14_keviyot :
    keviyot14.length = 14 ∧ keviyot14.Nodup ∧
    (∀ y, 1 ≤ y → keviyah y ∈ keviyot14) ∧ (∀ k ∈ keviyot14, ∃ y, 1 ≤ y ∧ keviyah y = k) :=
  ⟨keviyot14_length, keviyot14_nodup, keviyah_mem_keviyot14, keviyot14_occur⟩

/-! ## Periodicity -/

/-- 689472 years = 36288 cycles = 8527680 months = 251827457 days = 35975351 weeks. -/
theorem greatPeriod_arith :
    greatPeriod = 19 * 36288 ∧ 36288 * 235 * lunation = 251827457 * partsPerDay ∧
    251827457 = 7 * 35975351 := by decide

theorem molad_add_greatPeriod (y : Nat) (hy : 1 ≤ y) :
    molad (y + greatPeriod) = molad y + partsPerWeek * 35975351 := by
  unfold molad
  rw [show y + greatPeriod = y + 19 * 36288 by rfl, elapsedMonths_add_cycles y 36288 hy]
  simp only [baharad, lunation, partsPerWeek, partsPerDay, partsPerHour]
  omega

theorem isLeap_add_greatPeriod (y : Nat) : isLeap (y + greatPeriod) = isLeap y := by
  simp only [isLeap_eq_dr, drLeap]
  have : 7 * (y + greatPeriod) + 1 = (7 * y + 1) + 19 * (7 * 36288) := by simp only [greatPeriod]; omega
  rw [this, Nat.add_mul_mod_self_left]

theorem roshHashanah_add_greatPeriod (y : Nat) (hy : 1 ≤ y) :
    roshHashanah (y + greatPeriod) = roshHashanah y + 7 * 35975351 := by
  unfold roshHashanah
  rw [molad_add_greatPeriod y hy, isLeap_add_greatPeriod, show y + greatPeriod - 1 = (y - 1) + greatPeriod by omega,
    isLeap_add_greatPeriod, fixRH_add_weeks]

/-- **(d) Periodicity**: keviyah(y + 689472) = keviyah(y) for every year y ≥ 1. -/
theorem keviyah_period (y : Nat) (hy : 1 ≤ y) : keviyah (y + greatPeriod) = keviyah y := by
  unfold keviyah yearLength
  rw [show y + greatPeriod + 1 = (y + 1) + greatPeriod by omega,
    roshHashanah_add_greatPeriod y hy, roshHashanah_add_greatPeriod (y + 1) (by omega)]
  simp only [weekday, Prod.mk.injEq]
  omega

theorem isPeriod_greatPeriod : IsPeriod greatPeriod := keviyah_period

/-! ## Minimality of the period -/

theorem IsPeriod.zero : IsPeriod 0 := fun _ _ => rfl

theorem IsPeriod.add {a b : Nat} (ha : IsPeriod a) (hb : IsPeriod b) : IsPeriod (a + b) := by
  intro y hy
  rw [← Nat.add_assoc, hb (y + a) (by omega), ha y hy]

theorem IsPeriod.mul {a : Nat} (ha : IsPeriod a) : ∀ k, IsPeriod (a * k)
  | 0 => by simpa using IsPeriod.zero
  | k + 1 => by rw [Nat.mul_succ]; exact (IsPeriod.mul ha k).add ha

theorem IsPeriod.sub {a b : Nat} (ha : IsPeriod a) (hb : IsPeriod b) (hba : b ≤ a) :
    IsPeriod (a - b) := by
  intro y hy
  have h1 := hb (y + (a - b)) (by omega)
  rw [show y + (a - b) + b = y + a by omega, ha y hy] at h1
  exact h1.symm

theorem IsPeriod.mod {a b : Nat} (ha : IsPeriod a) (hb : IsPeriod b) : IsPeriod (a % b) := by
  have h := Nat.mod_add_div a b
  have : a % b = a - b * (a / b) := by omega
  rw [this]
  exact ha.sub (hb.mul _) (by omega)

theorem IsPeriod.gcd {a b : Nat} (ha : IsPeriod a) (hb : IsPeriod b) : IsPeriod (Nat.gcd a b) := by
  induction a, b using Nat.gcd.induction with
  | H0 n => simpa using hb
  | H1 m n _ ih => rw [Nat.gcd_rec]; exact ih (hb.mod ha) ha

/-- For each prime p ∣ 689472 = 2⁶·3⁴·7·19, the maximal proper divisor 689472/p is not a
period: year 1 and year 1 + 689472/p have different keviyot (kernel `decide`). -/
theorem not_period_half : keviyah (1 + greatPeriod / 2) ≠ keviyah 1 := by decide
theorem not_period_third : keviyah (1 + greatPeriod / 3) ≠ keviyah 1 := by decide
theorem not_period_seventh : keviyah (1 + greatPeriod / 7) ≠ keviyah 1 := by decide
theorem not_period_nineteenth : keviyah (1 + greatPeriod / 19) ≠ keviyah 1 := by decide

theorem coprime_of_not_dvd (k p : Nat) (hp : ∀ s, s < p → s ≠ 0 → Nat.gcd s p = 1)
    (hpos : 0 < p) (h : ¬ p ∣ k) : Nat.Coprime k p := by
  have hs : k % p ≠ 0 := fun h0 => h (Nat.dvd_of_mod_eq_zero h0)
  unfold Nat.Coprime
  rw [Nat.gcd_comm, Nat.gcd_rec]
  exact hp _ (Nat.mod_lt _ hpos) hs

/-- **(e) Minimality**: no positive d < 689472 is a period of the keviyah sequence. So
689472 is the least period (and every period is a multiple of it, by `IsPeriod.gcd`). -/
theorem greatPeriod_minimal (d : Nat) (hd0 : 0 < d) (hd : d < greatPeriod) : ¬ IsPeriod d := by
  intro hP
  have hg := hP.gcd isPeriod_greatPeriod
  -- g = gcd d N is a period, 0 < g < N, g ∣ N
  have hgN : Nat.gcd d greatPeriod ∣ greatPeriod := Nat.gcd_dvd_right _ _
  obtain ⟨k, hk⟩ := hgN
  have hgpos : 0 < Nat.gcd d greatPeriod := Nat.gcd_pos_of_pos_left _ hd0
  have hgle : Nat.gcd d greatPeriod ≤ d := Nat.gcd_le_left _ hd0
  generalize Nat.gcd d greatPeriod = g at hg hk hgpos hgle
  have hk1 : 1 < k := by
    rcases k with _ | _ | k
    · simp at hk
    · simp at hk; omega
    · omega
  have contra : ∀ p j, k = p * j → greatPeriod / p = g * j → ¬ IsPeriod (greatPeriod / p) →
      False := fun p j _ hq hn => hn (hq ▸ hg.mul j)
  by_cases h2 : 2 ∣ k
  · obtain ⟨j, rfl⟩ := h2
    refine contra 2 j rfl ?_ (fun h => not_period_half (h 1 (by decide)))
    rw [hk, Nat.mul_left_comm, Nat.mul_div_cancel_left _ (by decide)]
  by_cases h3 : 3 ∣ k
  · obtain ⟨j, rfl⟩ := h3
    refine contra 3 j rfl ?_ (fun h => not_period_third (h 1 (by decide)))
    rw [hk, Nat.mul_left_comm, Nat.mul_div_cancel_left _ (by decide)]
  by_cases h7 : 7 ∣ k
  · obtain ⟨j, rfl⟩ := h7
    refine contra 7 j rfl ?_ (fun h => not_period_seventh (h 1 (by decide)))
    rw [hk, Nat.mul_left_comm, Nat.mul_div_cancel_left _ (by decide)]
  by_cases h19 : 19 ∣ k
  · obtain ⟨j, rfl⟩ := h19
    refine contra 19 j rfl ?_ (fun h => not_period_nineteenth (h 1 (by decide)))
    rw [hk, Nat.mul_left_comm, Nat.mul_div_cancel_left _ (by decide)]
  -- k is coprime to 2, 3, 7, 19, hence to 689472 = 2^6 * 3^4 * 7 * 19; but k ∣ 689472.
  have c2 := coprime_of_not_dvd k 2 (by decide) (by decide) h2
  have c3 := coprime_of_not_dvd k 3 (by decide) (by decide) h3
  have c7 := coprime_of_not_dvd k 7 (by decide) (by decide) h7
  have c19 := coprime_of_not_dvd k 19 (by decide) (by decide) h19
  have cN : Nat.Coprime k (2 ^ 6 * 3 ^ 4 * 7 * 19) :=
    Nat.Coprime.mul_right (Nat.Coprime.mul_right (Nat.Coprime.mul_right
      (Nat.Coprime.pow_right 6 c2) (Nat.Coprime.pow_right 4 c3)) c7) c19
  have hkN : k ∣ 2 ^ 6 * 3 ^ 4 * 7 * 19 :=
    ⟨g, by have e : (2 ^ 6 * 3 ^ 4 * 7 * 19 : Nat) = greatPeriod := by decide
           rw [e, hk, Nat.mul_comm]⟩
  have := Nat.Coprime.eq_one_of_dvd cN hkN
  omega

end Hebrew
