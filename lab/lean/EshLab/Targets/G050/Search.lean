/-
EshLab.Targets.G050.Search -- a small *verified* checker / exhaustive search.

Idea.  A colouring of `{1,…,n}` is read left to right.  `pre c m` is the list of the
colours (as `Nat`s) of `1, …, m`.  A local test `ok l j` says "colouring the next integer
`l.length + 1` with colour `j` creates no bad configuration whose largest element is that
integer".  We prove, for Schur and for vdW:

  `SchurFree k n c  ↔  ∀ m < n, schurOk (pre c m) (c (m+1)).val = true`   (`schurFree_iff`)
  `APFree k L n c   ↔  ∀ m < n, apOk L (pre c m) (c (m+1)).val = true`   (`apFree_iff`, L ≥ 2)

Lower bounds: the right-hand side for an explicit colouring is a closed Boolean computation,
evaluated by the kernel (`decide +kernel`).

Upper bounds: `layer ok k m` is the list of all colour-lists of length `m` all of whose
steps pass `ok` (breadth-first exhaustive search, no symmetry breaking).  `pre_mem_layer`
proves that every good colouring appears in it; hence `layer ok k (n) = []` (a closed
computation, again checked by the kernel) implies that no good colouring of `{1,…,n}`
exists.  No SAT solver is trusted here.
-/
import EshLab.Targets.G050.Defs

namespace EshLab.G050

/-- Colours of `1, …, m` as natural numbers. -/
def pre {k : Nat} (c : Nat → Fin k) (m : Nat) : List Nat :=
  (List.range m).map fun i => (c (i + 1)).val

theorem pre_length {k : Nat} (c : Nat → Fin k) (m : Nat) : (pre c m).length = m := by
  simp [pre]

theorem pre_getD {k : Nat} (c : Nat → Fin k) {m i : Nat} (h : i < m) :
    (pre c m).getD i 0 = (c (i + 1)).val := by
  simp [pre, List.getD_eq_getElem?_getD, h]

theorem pre_succ {k : Nat} (c : Nat → Fin k) (m : Nat) :
    pre c (m + 1) = pre c m ++ [(c (m + 1)).val] := by
  simp [pre, List.range_succ]

/-! ### Local tests -/

/-- Schur test for the new integer `z = l.length + 1` with colour `j`: for every split
`z = x + y` (`x = i + 1`, `y = z - x`, both `≥ 1`) not both `x` and `y` have colour `j`. -/
def schurOk (l : List Nat) (j : Nat) : Bool :=
  (List.range l.length).all fun i =>
    !(l.getD i 0 == j && l.getD (l.length - 1 - i) 0 == j)

/-- AP test for the new integer `z = l.length + 1` with colour `j`: for every difference
`d = d₀ + 1` with `a := z - (L-1)d ≥ 1`, the terms `a + t d` (`t < L - 1`) are not all of
colour `j`. -/
def apOk (L : Nat) (l : List Nat) (j : Nat) : Bool :=
  (List.range l.length).all fun d₀ =>
    if (L - 1) * (d₀ + 1) ≤ l.length then
      !((List.range (L - 1)).all fun t =>
          l.getD (l.length - (L - 1) * (d₀ + 1) + t * (d₀ + 1)) 0 == j)
    else true

/-! ### The local tests characterise the global properties -/

theorem schurFree_iff {k n : Nat} (c : Nat → Fin k) :
    SchurFree k n c ↔ ∀ m, m < n → schurOk (pre c m) (c (m + 1)).val = true := by
  constructor
  · intro h m hm
    simp only [schurOk, List.all_eq_true, List.mem_range, pre_length]
    intro i hi
    rw [pre_getD c hi, pre_getD c (by omega)]
    have hxy := h (i + 1) (m - i) (by omega) (by omega) (by omega)
    have e1 : i + 1 + (m - i) = m + 1 := by omega
    have e2 : m - 1 - i + 1 = m - i := by omega
    rw [e1] at hxy
    rw [e2]
    cases h1 : (c (i + 1)).val == (c (m + 1)).val <;>
      cases h2 : (c (m - i)).val == (c (m + 1)).val <;> simp_all [Fin.ext_iff]
  · intro h x y hx hy hxy hmono
    have := h (x + y - 1) (by omega)
    simp only [schurOk, List.all_eq_true, List.mem_range, pre_length] at this
    have h2 := this (x - 1) (by omega)
    rw [pre_getD c (by omega), pre_getD c (by omega)] at h2
    have e1 : x - 1 + 1 = x := by omega
    have e2 : x + y - 1 - 1 - (x - 1) + 1 = y := by omega
    have e3 : x + y - 1 + 1 = x + y := by omega
    rw [e1, e2, e3] at h2
    simp [hmono.1, hmono.2] at h2

/-- Arithmetic helper: for `t < L - 1`, the AP term `a + t d` lies in `[1, m]` when
`a + (L - 1) d = m + 1`, `a ≥ 1`, `d ≥ 1`. -/
private theorem ap_index {L m a d t : Nat} (hd : 1 ≤ d) (ht : t < L - 1)
    (hlast : a + (L - 1) * d = m + 1) : a + t * d ≤ m := by
  have : t * d < (L - 1) * d := Nat.mul_lt_mul_of_pos_right ht hd
  omega

theorem apFree_iff {k L n : Nat} (hL : 2 ≤ L) (c : Nat → Fin k) :
    APFree k L n c ↔ ∀ m, m < n → apOk L (pre c m) (c (m + 1)).val = true := by
  constructor
  · intro h m hm
    simp only [apOk, List.all_eq_true, List.mem_range, pre_length]
    intro d₀ _
    split
    · rename_i hle
      -- a = m + 1 - (L-1) d
      generalize hD : (L - 1) * (d₀ + 1) = D at hle
      have hpos : 0 < D := by
        rw [← hD]; exact Nat.mul_pos (by omega) (by omega)
      simp only [Bool.not_eq_true', List.all_eq_false, List.mem_range]
      apply Classical.byContradiction
      intro hall
      simp only [not_exists, not_and, beq_iff_eq] at hall
      apply h (m + 1 - D) (d₀ + 1) (by omega) (by omega) (by omega)
      have key : ∀ t, t < L - 1 → c (m + 1 - D + t * (d₀ + 1)) = c (m + 1) := by
        intro t ht
        have hidx : m + 1 - D + t * (d₀ + 1) ≤ m :=
          ap_index (a := m + 1 - D) (by omega) ht (by omega)
        have := hall t ht
        rw [pre_getD c (by omega)] at this
        have e : m - D + t * (d₀ + 1) + 1 = m + 1 - D + t * (d₀ + 1) := by omega
        rw [e] at this
        exact Fin.ext (Classical.not_not.mp this)
      intro i hi
      have h0 := key 0 (by omega)
      simp only [Nat.zero_mul, Nat.add_zero] at h0
      rw [h0]
      by_cases hi' : i < L - 1
      · exact key i hi'
      · have : i = L - 1 := by omega
        subst this
        rw [hD]; congr 1; omega
    · rfl
  · intro h a d ha hd hlast hall
    generalize hD : (L - 1) * d = D at hlast
    have hpos : 0 < D := by
      rw [← hD]; exact Nat.mul_pos (by omega) hd
    have hd' : d - 1 < a + D - 1 := by
      have : d ≤ D := by rw [← hD]; exact Nat.le_mul_of_pos_left d (by omega)
      omega
    have := h (a + D - 1) (by omega)
    simp only [apOk, List.all_eq_true, List.mem_range, pre_length] at this
    have h2 := this (d - 1) hd'
    have e : d - 1 + 1 = d := by omega
    rw [e, hD] at h2
    rw [if_pos (by omega)] at h2
    simp only [Bool.not_eq_true', List.all_eq_false, List.mem_range] at h2
    obtain ⟨t, ht, hne⟩ := h2
    have hidx : a + t * d ≤ a + D - 1 := by
      have := ap_index (m := a + D - 1) (a := a) hd ht (by rw [hD]; omega)
      exact this
    rw [pre_getD c (by omega)] at hne
    have e2 : a + D - 1 - D + t * d + 1 = a + t * d := by omega
    have e3 : a + D - 1 + 1 = a + (L - 1) * d := by omega
    rw [e2, e3] at hne
    have h1 := hall t (by omega)
    have h3 := hall (L - 1) (by omega)
    rw [h1, h3] at hne
    simp at hne

/-! ### Exhaustive breadth-first search -/

/-- Extend every list in `ls` by every colour `j < k` that passes `ok`. -/
def extend (ok : List Nat → Nat → Bool) (k : Nat) (ls : List (List Nat)) : List (List Nat) :=
  ls.flatMap fun l => ((List.range k).filter (ok l)).map fun j => l ++ [j]

/-- All colour-lists of length `m` every step of which passes `ok`. -/
def layer (ok : List Nat → Nat → Bool) (k : Nat) : Nat → List (List Nat)
  | 0 => [[]]
  | m + 1 => extend ok k (layer ok k m)

/-- Soundness of the search: every colouring whose steps pass `ok` is found. -/
theorem pre_mem_layer (ok : List Nat → Nat → Bool) {k : Nat} (c : Nat → Fin k) :
    ∀ n, (∀ m, m < n → ok (pre c m) (c (m + 1)).val = true) → pre c n ∈ layer ok k n := by
  intro n
  induction n with
  | zero => intro _; simp [pre, layer]
  | succ n ih =>
    intro h
    have hn := ih (fun m hm => h m (by omega))
    simp only [layer, extend, List.mem_flatMap, List.mem_map, List.mem_filter, List.mem_range]
    exact ⟨pre c n, hn, (c (n + 1)).val, ⟨(c (n + 1)).isLt, h n (by omega)⟩, (pre_succ c n).symm⟩

/-- Upper-bound principle: if the search finds nothing at depth `n`, no `k`-colouring of
`{1,…,n}` passes all local tests. -/
theorem no_colouring_of_layer_nil (ok : List Nat → Nat → Bool) {k n : Nat}
    (hnil : layer ok k n = []) (c : Nat → Fin k) :
    ¬ ∀ m, m < n → ok (pre c m) (c (m + 1)).val = true := by
  intro h
  have := pre_mem_layer ok c n h
  rw [hnil] at this
  simp at this

/-! ### Explicit colourings from lists -/

/-- The colouring given by a list: integer `x ≥ 1` gets colour `l[x-1] mod k`
(and `0` gets `l[0]`; irrelevant).  For a list with entries `< k` the `mod` does nothing. -/
def ofList (k : Nat) (hk : 0 < k) (l : List Nat) : Nat → Fin k :=
  fun x => ⟨l.getD (x - 1) 0 % k, Nat.mod_lt _ hk⟩

/-- Boolean form of "all steps pass `ok`", for computation. -/
def allSteps (ok : List Nat → Nat → Bool) {k : Nat} (c : Nat → Fin k) (n : Nat) : Bool :=
  (List.range n).all fun m => ok (pre c m) (c (m + 1)).val

theorem allSteps_iff (ok : List Nat → Nat → Bool) {k : Nat} (c : Nat → Fin k) (n : Nat) :
    allSteps ok c n = true ↔ ∀ m, m < n → ok (pre c m) (c (m + 1)).val = true := by
  simp [allSteps]

end EshLab.G050
