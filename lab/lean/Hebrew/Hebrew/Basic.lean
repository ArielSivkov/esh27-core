/-!
# The fixed Hebrew calendar after the Rambam (core Lean, no Mathlib)

Definitions follow Mishneh Torah, Hilchot Kiddush HaChodesh (הלכות קידוש החודש),
chapters 6–8. Hebrew text: Sefaria "Torat Emet 363"; English: Touger (Moznaim).
Exact excerpts and references: `lab/experiments/hebrew-calendar/SOURCES.md`.

Conventions (ours, not the Rambam's wording):
* Time is counted in חלקים (parts) from the start (nightfall, 6 PM) of day index 0,
  which is the Sunday ("יום ראשון") of the week of molad BaHaRaD.
* A day index `d` has weekday `weekday d = d % 7 + 1` (1 = יום ראשון … 7 = שבת),
  the Rambam's numbering "באחד בשבת … בשבת".
* Hours are counted from nightfall, as in the Rambam's סימנים (e.g. ג"ט ר"ד).
-/

namespace Hebrew

/-- "וְהַשָּׁעָה מְחֻלֶּקֶת לְאֶלֶף וּשְׁמוֹנִים חֲלָקִים" — "An hour can be divided into
1080 units" (Kiddush HaChodesh 6:2). -/
abbrev partsPerHour : Nat := 1080

/-- "הַיּוֹם וְהַלַּיְלָה אַרְבַּע וְעֶשְׂרִים שָׁעוֹת" — "Day and night are … a twenty-four hour
composite" (6:2). 24 · 1080 = 25920 parts. -/
abbrev partsPerDay : Nat := 25920

/-- One week = 7 · 25920 = 181440 parts. -/
abbrev partsPerWeek : Nat := 181440

/-- "תִּשְׁעָה וְעֶשְׂרִים יוֹם וּשְׁתֵּים עֶשְׂרֵה שָׁעוֹת … וּשְׁבַע מֵאוֹת וּשְׁלֹשָׁה וְתִשְׁעִים
חֲלָקִים … וְזֶה הוּא הַזְּמַן שֶׁבֵּין כָּל מוֹלָד וּמוֹלָד" — "twenty-nine full days, twelve hours …
and 793 units … This is the interval between one conjunction and the next" (6:3).
29 d 12 h 793 p = 765433 parts. -/
abbrev lunation : Nat := 765433

theorem lunation_eq : lunation = 29 * partsPerDay + 12 * partsPerHour + 793 := rfl

/-- Molad BaHaRaD: "וְהוּא הָיָה בְּלֵיל שֵׁנִי חָמֵשׁ שָׁעוֹת בַּלַּיְלָה וּמָאתַיִם וְאַרְבָּעָה
חֲלָקִים. סִימָן לָהֶם בהר"ד" — "on Monday night, 5 hours and 204 units after nightfall"
(6:8; also 6:13 "מוֹלַד תְּחִלַּת הַמַּחֲזוֹר הָרִאשׁוֹן הָיָה לבהר"ד").
Day index 1 (= יום שני), 5 h, 204 p. -/
abbrev baharad : Nat := 1 * partsPerDay + 5 * partsPerHour + 204

theorem baharad_eq : baharad = 31524 := rfl

/-- Weekday 1..7 of a day index (1 = Sunday "אחד בשבת", 7 = Shabbat). -/
abbrev weekday (d : Nat) : Nat := d % 7 + 1

/-- Position 1..19 of year `y` in its 19-year cycle (מחזור), year 1 being the first
year of the first cycle (6:10, 6:13). Year 0 is treated as year 19 of the cycle before. -/
def cycleYear (y : Nat) : Nat := (y + 18) % 19 + 1

/-- "הַשֶּׁבַע שָׁנִים הַמְעֻבָּרוֹת שֶׁבְּכָל מַחֲזוֹר … הֵם שָׁנָה שְׁלִישִׁית מִן הַמַּחֲזוֹר וְשִׁשִּׁית
וּשְׁמִינִית וּשְׁנַת אַחַת עֶשְׂרֵה וּשְׁנַת אַרְבַּע עֶשְׂרֵה וּשְׁנַת שְׁבַע עֶשְׂרֵה וּשְׁנַת י"ט.
סִימָן לָהֶם גו"ח י"א י"ד י"ז י"ט" — "The seven leap years in each cycle … the third, sixth,
eighth, eleventh, fourteenth, seventeenth, nineteenth year" (6:11). -/
def leapCycleYear : Nat → Bool
  | 3 | 6 | 8 | 11 | 14 | 17 | 19 => true
  | _ => false

/-- Year `y` is a leap year (מעוברת, 13 months) iff its place in the cycle is
גו"ח י"א י"ד י"ז י"ט (6:11). -/
def isLeap (y : Nat) : Bool := leapCycleYear (cycleYear y)

/-- Number of months in the first `r` years of a cycle (r = 0..18), i.e. 12 per common
year and 13 per leap year of גו"ח י"א י"ד י"ז י"ט (6:11, 6:14). -/
def monthsBeforeInCycle : Nat → Nat
  | 0 => 0   | 1 => 12  | 2 => 24  | 3 => 37  | 4 => 49
  | 5 => 61  | 6 => 74  | 7 => 86  | 8 => 99  | 9 => 111
  | 10 => 123 | 11 => 136 | 12 => 148 | 13 => 160 | 14 => 173
  | 15 => 185 | 16 => 197 | 17 => 210 | 18 => 222
  | _ => 0

/-- Months elapsed from molad BaHaRaD to the molad of Tishrei of year `y` (y ≥ 1):
"תִּקַּח שְׁנֵי יְצִירָה שֶׁעָבְרוּ וְגָמְרוּ וְתַעֲשֶׂה אוֹתָם מַחֲזוֹרִין שֶׁל תְּשַׁע עֶשְׂרֵה … וְתֵדַע
מִנְיַן הַמַּחֲזוֹרִין שֶׁעָבְרוּ וּמִנְיַן הַשָּׁנִים שֶׁעָבְרוּ מִמַּחֲזוֹר שֶׁעֲדַיִן לֹא נִשְׁלַם" — "take the
years of creation that have passed … group them in nineteen-year cycles … the number of
cycles that have passed and the number of years … of the cycle not yet completed"
(6:14). Each full cycle has 12·12 + 7·13 = 235 months (6:10). -/
def elapsedMonths (y : Nat) : Nat :=
  235 * ((y - 1) / 19) + monthsBeforeInCycle ((y - 1) % 19)

/-- Molad Tishrei of year `y`, in parts from the start of day index 0:
BaHaRaD plus the elapsed lunations (6:8, 6:13–14: "מוֹלַד הַשָּׁנָה הוּא מוֹלַד תִּשְׁרֵי"). -/
def molad (y : Nat) : Nat := baharad + elapsedMonths y * lunation

/-- Day index of the molad. -/
def moladDay (y : Nat) : Nat := molad y / partsPerDay
/-- Time of the molad within its day, in parts from nightfall. -/
def moladTime (y : Nat) : Nat := molad y % partsPerDay

/-! ## The four dechiyot (Kiddush HaChodesh 7:1–6) -/

/-- Lo ADU: "אֵין קוֹבְעִין לְעוֹלָם רֹאשׁ חֹדֶשׁ תִּשְׁרֵי … לֹא בְּאֶחָד בְּשַׁבָּת וְלֹא בִּרְבִיעִי
בְּשַׁבָּת וְלֹא בְּעֶרֶב שַׁבָּת. סִימָן לָהֶם אד"ו" — "Rosh Chodesh Tishrei should never be
established on a Sunday, a Wednesday, or a Friday" (7:1). -/
abbrev isADU (d : Nat) : Prop := weekday d = 1 ∨ weekday d = 4 ∨ weekday d = 6

/-- Molad zaken: "אִם יִהְיֶה הַמּוֹלָד בַּחֲצִי הַיּוֹם אוֹ לְמַעְלָה מֵחֲצִי הַיּוֹם קוֹבְעִין רֹאשׁ
חֹדֶשׁ בַּיּוֹם שֶׁלְּאַחֲרָיו" — "if the conjunction takes place at noon or after noon, Rosh
Chodesh should be established on the following day" (7:2). Noon = 18 h from nightfall. -/
abbrev moladZaken (h : Nat) : Prop := 18 * partsPerHour ≤ h

/-- GaTRaD: "מוֹלַד תִּשְׁרֵי … בְּלֵיל שְׁלִישִׁי בְּתֵשַׁע שָׁעוֹת בַּלַּיְלָה וּמָאתַיִם וְאַרְבָּעָה
חֲלָקִים … סִימָנָהּ ג"ט ר"ד. אוֹ יוֹתֵר עַל זֶה. אִם הָיְתָה שָׁנָה פְּשׁוּטָה … אֵין קוֹבְעִים אוֹתוֹ
בִּשְׁלִישִׁי … אֶלָּא בַּחֲמִישִׁי" — "In an ordinary year, when the conjunction … falls on the
night of the third day, nine hours and 204 units … or more … it is established on
Thursday" (7:4). -/
abbrev gatrad (leap : Bool) (d h : Nat) : Prop :=
  leap = false ∧ weekday d = 3 ∧ 9 * partsPerHour + 204 ≤ h

/-- BeTU'TaKPaT: "אִם יָצָא מוֹלַד תִּשְׁרֵי בְּיוֹם שֵׁנִי בְּשָׁלֹשׁ שָׁעוֹת בְּיוֹם וְתקפ"ט חֲלָקִים
… סִימָנָהּ בט"ו תקפ"ט. אוֹ יֶתֶר עַל כֵּן. אִם הָיְתָה … הַשָּׁנָה הַסְּמוּכָה לָהּ שֶׁעָבְרָה מְעֻבֶּרֶת.
אֵין קוֹבְעִין … בְּשֵׁנִי … אֶלָּא בִּשְׁלִישִׁי" — "in a year that follows a leap year: if the
conjunction … takes place on Monday, three hours and 589 units or more after daybreak
(2-15-589) … it is established on Tuesday" (7:5). -/
abbrev betutakpat (prevLeap : Bool) (d h : Nat) : Prop :=
  prevLeap = true ∧ weekday d = 2 ∧ 15 * partsPerHour + 589 ≤ h

/-- Day index of Rosh Hashana for a year whose molad is `t` (parts), given whether the
year is a leap year and whether the previous year was. This is the procedure of 7:6:
"וְיוֹם הַמּוֹלָד הוּא יוֹם הַקְּבִיעָה לְעוֹלָם. אֶלָּא אִם כֵּן הָיָה בְּאֶחָד בְּשַׁבָּת אוֹ
בִּרְבִיעִי אוֹ בְּעֶרֶב שַׁבָּת. אוֹ אִם הָיָה הַמּוֹלָד בַּחֲצוֹת הַיּוֹם אוֹ אַחַר חֲצוֹת. אוֹ … ג"ט ר"ד
… וְהָיְתָה שָׁנָה פְּשׁוּטָה. אוֹ … בט"ו תקפ"ט … וְהָיְתָה הַשָּׁנָה פְּשׁוּטָה שֶׁאַחַר הַמְעֵבֶּרֶת …
אֵין קוֹבְעִין בְּיוֹם הַמּוֹלָד אֶלָּא בַּיּוֹם שֶׁלְּאַחֲרָיו אוֹ שֶׁלְּאַחַר אַחֲרָיו" — "The day of the
conjunction will be the day of Rosh Chodesh, except … [the four cases] … then it is
established on the day that follows, or on the day following that" (7:6).

Implementation: zaken, GaTRaD and BeTU'TaKPaT move the day by one; then, if the day
reached is אד"ו, by one more (7:1, 7:3). GaTRaD's "Tuesday → Thursday" (7:4) is the
composite "→ Wednesday (אד"ו) → Thursday". -/
def fixRH (t : Nat) (leap prevLeap : Bool) : Nat :=
  let d := t / partsPerDay
  let h := t % partsPerDay
  let d1 := if moladZaken h ∨ gatrad leap d h ∨ betutakpat prevLeap d h then d + 1 else d
  if isADU d1 then d1 + 1 else d1

/-- Day index of Rosh Hashana (א' תשרי) of year `y`. -/
def roshHashanah (y : Nat) : Nat := fixRH (molad y) (isLeap y) (isLeap (y - 1))

/-- Length of year `y` in days: "תֵּדַע תְּחִלָּה יוֹם שֶׁנִּקְבַּע בּוֹ רֹאשׁ הַשָּׁנָה … וְתֵדַע יוֹם
שֶׁיִּקָּבַע בּוֹ רֹאשׁ הַשָּׁנָה שֶׁלְּאַחֲרֶיהָ" — "determine the day on which Rosh HaShanah will
fall … then … in the year that follows" (8:7). -/
def yearLength (y : Nat) : Nat := roshHashanah (y + 1) - roshHashanah y

/-- The keviyah (קביעות השנה) of year `y`: (weekday of Rosh Hashana, length of year).
Since lengths 353–355 are common and 383–385 leap years, this also determines whether
the year is פשוטה/מעוברת and חסרה/כסדרה/שלמה (8:6–8). -/
def keviyah (y : Nat) : Nat × Nat := (weekday (roshHashanah y), yearLength y)

/-- Year `y` is "חסרה" (both Marcheshvan and Kislev lacking), "כסדרן" or "שלמה" by the
day count of 8:7–8; we record it as 0/1/2 above the minimum (353 or 383). -/
def yearKind (y : Nat) : Nat := yearLength y - (if isLeap y then 383 else 353)

/-! ## Dershowitz–Reingold arithmetic (the oracle `hebrew_period.py`) -/

/-- D–R leap test `(7y+1) mod 19 < 7`. -/
def drLeap (y : Nat) : Bool := decide ((7 * y + 1) % 19 < 7)
/-- D–R elapsed months `⌊(235y − 234)/19⌋`. -/
def drElapsedMonths (y : Nat) : Nat := (235 * y - 234) / 19

/-- D–R "elapsed days" with only the first two dechiyot (molad zaken folded into the
constant 12084 = 11 h 204 p, i.e. BaHaRaD shifted by 6 h; lo ADU via `3(d+1) mod 7 < 3`);
transcribed from `ny0` in `hebrew_period.py`. Day numbers are 1 less than ours. -/
def drDelay1 (y : Nat) : Nat :=
  let m := drElapsedMonths y
  let day := 29 * m + (12084 + 13753 * m) / 25920
  if (3 * (day + 1)) % 7 < 3 then day + 1 else day

/-- D–R new-year day: the 3rd and 4th dechiyot expressed as "a year may not have 356
days" and "a year may not have 382 days" (`ny` in `hebrew_period.py`). -/
def drNewYear (y : Nat) : Nat :=
  let a := drDelay1 y
  if drDelay1 (y + 1) - a = 356 then a + 2
  else if a - drDelay1 (y - 1) = 382 then a + 1
  else a

/-- The 7 keviyot of common years (פשוטות), as (weekday of RH, length). -/
def keviyotCommon : List (Nat × Nat) :=
  [(2, 353), (2, 355), (3, 354), (5, 354), (5, 355), (7, 353), (7, 355)]
/-- The 7 keviyot of leap years (מעוברות). -/
def keviyotLeap : List (Nat × Nat) :=
  [(2, 383), (2, 385), (3, 384), (5, 383), (5, 385), (7, 383), (7, 385)]
/-- The 14 keviyot, as (weekday of RH, length): 7 common + 7 leap. -/
def keviyot14 : List (Nat × Nat) := keviyotCommon ++ keviyotLeap

/-- `p` is a period of the keviyah sequence (on years ≥ 1). -/
def IsPeriod (p : Nat) : Prop := ∀ y, 1 ≤ y → keviyah (y + p) = keviyah y

/-- 689472 = 19 · 36288 years ("the great period"). -/
abbrev greatPeriod : Nat := 689472

end Hebrew
