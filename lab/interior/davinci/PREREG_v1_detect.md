# Da Vinci v1: window detection with foundation models (pre-registration, 2026-11-24)

Ariel: "שיבנו ואז ישוו לתמונה... תנסה לראות אם יש איזה פאונדיישן מודל" ("let them build, then compare to the photo...
see if there's some foundation model").

**Hypothesis:** an open-vocabulary detector finds windows as separate boxes. Grouping the boxes into rows gives the floor count
better than a chat model (VLM) and better than 1D rhythm (v0.1).

**Data:** the 41 twin-world renders (sets A+B, `renders/`; truth f from the tiles). Evaluated only on the **21 where the whole
building is in frame** (`fits`). Set A was already seen in v0.1, but nothing here is tuned on it: the parameters below are fixed
in advance.

**Arms:**
- (a) OWLv2 (google/owlv2-base-patch16-ensemble), query "a window", threshold 0.15.
- (b) Grounding DINO (IDEA-Research/grounding-dino-base), query "window.", box threshold 0.25.

**Floors from boxes:**
- Keep only boxes whose center is inside the building box.
- Sort by y-center and start a new row when the gap is > 0.6 × the median box height.
- Floors = the number of rows with ≥ 2 windows.

**Criterion, fixed:** ≥ 70% within ±1 floor, and better than the "always 4" baseline (on these 21).
Precision on towers is reported separately.

**Threats:**
- These are renders and not photos; real photos come after.
- f in the tiles may not match what the engine draws (to check).
- Small windows on distant towers at 480×720.
