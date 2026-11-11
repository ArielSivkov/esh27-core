/-
EshLab.Targets.G050.Counts -- exact COUNT of Schur-free 3-colourings of {1,…,13}.

Not imported by `EshLab.Targets.G050` (so the default `lake build` target is unchanged).
Build / check it from lab/lean/G050 with
    lake env lean ../EshLab/Targets/G050/Counts.lean
(after `lake build`, which compiles the imported Search module).

Statement (plain language).  Let `L13 := layer schurOk 3 13` be the list produced by the verified
breadth-first search of Search.lean.  Then
  * `L13` has exactly 18 entries and no duplicates;
  * a colouring `c : Nat → Fin 3` is Schur-free on {1,…,13} (`SchurFree 3 13 c`, x = y allowed)
    **iff** its colour word `pre c 13 = [c 1, …, c 13]` is one of the entries of `L13`;
  * every entry of `L13` is the colour word of some colouring.
Hence the map `c ↦ pre c 13` is a bijection between Schur-free 3-colourings of {1,…,13}
(as functions on {1,…,13}) and the 18 entries of `L13`: there are exactly 18 labelled
Schur 3-colourings of [1,13].
Further, exactly 3 entries of `L13` are restricted-growth words (colours appear in order of first
use: colour 0 first, colour 1 before colour 2), i.e. the 18 colourings form 3 orbits of the colour
permutation group S_3 (18 = 3 · 3!, every entry uses all three colours).  The "3 orbits" reading
is stated here only as this Boolean computation (`rgs_count`), not as a theorem about
quotients — see the honest note in lab/experiments/oeis/REPORT.md.

All proofs: `decide +kernel` + structural lemmas.  Axioms ⊆ {propext, Classical.choice, Quot.sound}.
-/
import EshLab.Targets.G050.Search

namespace EshLab.G050.Counts

open EshLab.G050

set_option maxHeartbeats 0

/-- Every word in `layer ok k m` has length `m`, and every step of it passes `ok`. -/
theorem mem_layer_steps (ok : List Nat → Nat → Bool) (k : Nat) :
    ∀ m l, l ∈ layer ok k m →
      l.length = m ∧ ∀ i, i < m → ok (l.take i) (l.getD i 0) = true := by
  intro m
  induction m with
  | zero => intro l hl; simp [layer] at hl; subst hl; simp
  | succ m ih =>
    intro l hl
    simp only [layer, extend, List.mem_flatMap, List.mem_map, List.mem_filter,
      List.mem_range] at hl
    obtain ⟨l0, hl0, j, ⟨_, hok⟩, rfl⟩ := hl
    obtain ⟨hlen, hsteps⟩ := ih l0 hl0
    refine ⟨by simp [hlen], ?_⟩
    intro i hi
    by_cases him : i < m
    · have e1 : (l0 ++ [j]).take i = l0.take i := by
        rw [List.take_append_of_le_length (by omega)]
      have e2 : (l0 ++ [j]).getD i 0 = l0.getD i 0 := by
        simp [List.getD_eq_getElem?_getD, List.getElem?_append_left (show i < l0.length by omega)]
      rw [e1, e2]; exact hsteps i him
    · have him' : i = m := by omega
      subst him'
      have e1 : (l0 ++ [j]).take i = l0 := by
        rw [List.take_append_of_le_length (by omega), List.take_of_length_le (by omega)]
      have e2 : (l0 ++ [j]).getD i 0 = j := by
        simp [List.getD_eq_getElem?_getD, hlen]
      rw [e1, e2]; exact hok

theorem pre_take {k : Nat} (c : Nat → Fin k) {i n : Nat} (h : i ≤ n) :
    (pre c n).take i = pre c i := by
  simp only [pre]; rw [← List.map_take, List.take_range, Nat.min_eq_left h]

/-- The 18-element list found by the verified search. -/
def L13 : List (List Nat) := layer schurOk 3 13

theorem L13_length : L13.length = 18 := by decide +kernel

theorem L13_nodup : L13.Nodup := by decide +kernel

/-- Soundness + completeness: Schur-free on {1..13} iff the colour word is in `L13`. -/
theorem schurFree_iff_mem (c : Nat → Fin 3) : SchurFree 3 13 c ↔ pre c 13 ∈ L13 := by
  constructor
  · intro h
    exact pre_mem_layer schurOk c 13 ((schurFree_iff c).1 h)
  · intro h
    apply (schurFree_iff c).2
    intro m hm
    have := (mem_layer_steps schurOk 3 13 (pre c 13) h).2 m hm
    rwa [pre_take c (Nat.le_of_lt hm), pre_getD c hm] at this

/-- Every entry of `L13` is realised by an actual colouring (so no entry is spurious). -/
theorem L13_realised : ∀ l ∈ L13, pre (ofList 3 (by decide) l) 13 = l := by
  have h : L13.all (fun l => pre (ofList 3 (by decide) l) 13 == l) = true := by decide +kernel
  intro l hl
  have := List.all_eq_true.1 h l hl
  simpa using this

/-- **Exactly 18** labelled Schur-free 3-colourings of {1,…,13}: the colour words of Schur-free
colourings are exactly the 18 distinct entries of `L13`. -/
theorem schur3_13_count :
    L13.length = 18 ∧ L13.Nodup ∧
    (∀ c : Nat → Fin 3, SchurFree 3 13 c ↔ pre c 13 ∈ L13) ∧
    (∀ l ∈ L13, ∃ c : Nat → Fin 3, pre c 13 = l) :=
  ⟨L13_length, L13_nodup, schurFree_iff_mem, fun l hl => ⟨_, L13_realised l hl⟩⟩

/-- Restricted-growth check: colours occur in order of first use (0, then 1, then 2, …). -/
def isRGS (l : List Nat) : Bool :=
  (l.foldl (fun (st : Bool × Nat) x =>
      (st.1 && x ≤ st.2, if x == st.2 then st.2 + 1 else st.2)) (true, 0)).1

/-- Exactly 3 of the 18 words are in canonical (restricted-growth) form, and every word uses
all three colours; so the 18 colourings are 3 orbits of size 3! = 6 (computational fact). -/
theorem rgs_count :
    (L13.filter isRGS).length = 3 ∧
    L13.all (fun l => l.contains 0 && l.contains 1 && l.contains 2) = true := by
  decide +kernel

end EshLab.G050.Counts

#print axioms EshLab.G050.Counts.schur3_13_count
#print axioms EshLab.G050.Counts.rgs_count
