/-
EshLab.Targets.G050.Defs -- STATEMENTS for goal G050 (small Schur and van der Waerden numbers).

Mathlib-free on purpose: this sub-library only needs core Lean 4, so it builds in seconds
on a fresh machine (see lakefile.toml, `lean_lib G050`).

Conventions
* A `k`-colouring is any function `c : Nat → Fin k`.  Only the values `c 1, …, c n` matter
  for statements about the interval `[1, n] = {1, …, n}`; the values at `0` and above `n`
  are ignored.  (Equivalent to colourings `Fin n → Fin k`, with `i : Fin n` standing for
  the integer `i + 1`; we use `Nat → Fin k` to avoid the off-by-one shift.)

Plain-language back-translation (failure mode #1 is stating the wrong thing):
* `SchurFree k n c`  : in the colouring `c` of `{1,…,n}` there are no `x, y ≥ 1` with
  `x + y ≤ n` such that `x`, `y`, `x + y` all get the same colour.  `x = y` is allowed,
  i.e. `x + x = 2x` monochromatic is also forbidden (classical Schur numbers,
  OEIS A030126: 1, 4, 13, 44, 160).
* `IsSchurNumber k s` : `{1,…,s}` has a Schur-free `k`-colouring but `{1,…,s+1}` has none.
  Together with monotonicity (`SchurFree.mono`) this says `s` is the LARGEST such `n`
  (`IsSchurNumber.iff`), i.e. `s = S(k)`.
* `APFree k L n c` : no `L`-term arithmetic progression `a, a+d, …, a+(L-1)d` with `a ≥ 1`,
  `d ≥ 1` and last term `≤ n` is monochromatic.
* `IsVdWNumber k L w` : `{1,…,w-1}` has an `APFree` `k`-colouring but every `k`-colouring of
  `{1,…,w}` contains a monochromatic `L`-AP; i.e. `w = W(k, L)` (`k` colours, length `L`;
  W(2,3) = 9, W(3,3) = 27, W(2,4) = 35).  `IsVdWNumber.iff` gives the "least n" reading.
-/

namespace EshLab.G050

/-- No monochromatic `x + y = z` with `1 ≤ x, y` and `z = x + y ≤ n`. -/
def SchurFree (k n : Nat) (c : Nat → Fin k) : Prop :=
  ∀ x y, 1 ≤ x → 1 ≤ y → x + y ≤ n → ¬ (c x = c (x + y) ∧ c y = c (x + y))

/-- `s` is the Schur number `S(k)`. -/
def IsSchurNumber (k s : Nat) : Prop :=
  (∃ c : Nat → Fin k, SchurFree k s c) ∧ ∀ c : Nat → Fin k, ¬ SchurFree k (s + 1) c

/-- No monochromatic `L`-term arithmetic progression with first term `≥ 1`, common
difference `≥ 1`, and last term `≤ n`. -/
def APFree (k L n : Nat) (c : Nat → Fin k) : Prop :=
  ∀ a d, 1 ≤ a → 1 ≤ d → a + (L - 1) * d ≤ n → ¬ ∀ i, i < L → c (a + i * d) = c a

/-- `w` is the van der Waerden number `W(k, L)`  (`k` colours, progressions of length `L`). -/
def IsVdWNumber (k L w : Nat) : Prop :=
  (∃ c : Nat → Fin k, APFree k L (w - 1) c) ∧ ∀ c : Nat → Fin k, ¬ APFree k L w c

/-! ### Monotonicity, and the "largest / least" reading of the definitions -/

theorem SchurFree.mono {k m n : Nat} {c : Nat → Fin k} (h : SchurFree k n c) (hmn : m ≤ n) :
    SchurFree k m c :=
  fun x y hx hy hxy => h x y hx hy (Nat.le_trans hxy hmn)

theorem APFree.mono {k L m n : Nat} {c : Nat → Fin k} (h : APFree k L n c) (hmn : m ≤ n) :
    APFree k L m c :=
  fun a d ha hd hlast => h a d ha hd (Nat.le_trans hlast hmn)

/-- If `IsSchurNumber k s` then `{1,…,n}` is Schur-`k`-colourable **iff** `n ≤ s`;
so `s` is exactly the largest such `n`. -/
theorem IsSchurNumber.iff {k s : Nat} (h : IsSchurNumber k s) (n : Nat) :
    (∃ c : Nat → Fin k, SchurFree k n c) ↔ n ≤ s := by
  constructor
  · intro ⟨c, hc⟩
    apply Nat.le_of_not_lt
    intro hlt
    exact h.2 c (hc.mono hlt)
  · intro hn
    obtain ⟨c, hc⟩ := h.1
    exact ⟨c, hc.mono hn⟩

/-- If `IsVdWNumber k L w` (with `w ≥ 1`) then `{1,…,n}` has an AP-free `k`-colouring
**iff** `n < w`; so `w` is the least `n` for which every colouring has a monochromatic
`L`-AP. -/
theorem IsVdWNumber.iff {k L w : Nat} (h : IsVdWNumber k L w) (hw : 1 ≤ w) (n : Nat) :
    (∃ c : Nat → Fin k, APFree k L n c) ↔ n < w := by
  constructor
  · intro ⟨c, hc⟩
    apply Nat.lt_of_not_le
    intro hle
    exact h.2 c (hc.mono hle)
  · intro hn
    obtain ⟨c, hc⟩ := h.1
    exact ⟨c, hc.mono (by omega)⟩

/-- The value of a Schur number is unique (so `IsSchurNumber k s` really pins `S(k)` down). -/
theorem IsSchurNumber.unique {k s t : Nat} (hs : IsSchurNumber k s) (ht : IsSchurNumber k t) :
    s = t := by
  have h1 := (hs.iff t).1 ht.1
  have h2 := (ht.iff s).1 hs.1
  omega

theorem IsVdWNumber.unique {k L v w : Nat} (hv : IsVdWNumber k L v) (hw : IsVdWNumber k L w)
    (hv1 : 1 ≤ v) (hw1 : 1 ≤ w) : v = w := by
  have h1 := (hv.iff hv1 (w - 1)).1 hw.1
  have h2 := (hw.iff hw1 (v - 1)).1 hv.1
  omega

end EshLab.G050
