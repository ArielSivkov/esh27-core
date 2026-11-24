# "Da Vinci's brain" v0: geometry instead of counting (pre-registration, 2026-11-24)

Ariel: "שיהיה לו מנוע גיאומטרי ממש חזק, עם צורות וצבעים... מנוע אדריכלות... דה וינצ'י" ("a really strong geometric engine, with shapes and
colors... an architecture engine... da Vinci").

**Idea: inverse architecture.** The world's facade engine (twin/buildings/src/facades.js) builds a facade from parameters:
type, floor count, colors. Da Vinci does the reverse. It looks at a building and pulls out its geometry:
- **floor pitch**, measured as the period of horizontal lines (autocorrelation) rather than by counting windows;
- **bay rhythm**, the horizontal period;
- **color palette** (k-means);
- **proportions.**

It returns parameters with ± uncertainty, which the engine can draw and compare against the photo (render-and-compare).

**Test v0, on synthetic ground truth (CPU, no GPU):**
- Screenshots taken from inside the twin world itself (swiftshader), at street level (1.6 m), from the nearest road node, facing
  buildings whose floor count `f` is known in the tiles. The facade engine draws exactly `f` floors, so the truth is known.
- Selection, fixed in advance: up to 24 buildings, stratified by f ∈ {2,3,4,8,20,30}, distance 25–80 m, chosen by
  a fixed seed (27).

**Measures:**
1. **Floors from the period** = (building height in pixels) / (period in pixels). Success: |error| ≤ 1 floor on ≥ 70% of images.
   Measured separately for low buildings (f ≤ 8) and towers.
2. **Baseline:** always guessing 4 (the most common value in the tiles). Da Vinci has to beat it.
3. **Palette:** reported only, with no criterion in v0.

**Threats:**
- The renderer draws regular floors, so this is easier than a real photo.
- A synthetic success does **not** prove success on photos; it only shows the method works where the truth is known.
- Facade occlusion by trees or other buildings is reported per image.
- The building's height in pixels comes from a mask derived from the known geometry; on a real photo it has to be estimated.
  v0 tests only the periodicity part.

## v0 result (2026-11-24, before any change). Negative.
- [F] Unclipped: 0/6 within ±1, against the baseline ("always 4") at 1/6.
- [F] In 15 of 21 images the building was not fully in the frame (a framing problem in the test).
- [F] The detected periods were mostly 8–13 px, which is window/texture detail rather than floors. Raw data: `results_v0.json`.

## Amendment A1 → v0.1 (written before the new test set)
Changes:
1. **Framing:** for each building, try up to 10 road nodes at distance [max(30, 0.9h), 3h], and keep the first one where the
   entire building box falls inside the frame with no point behind the camera. Otherwise the building is excluded and reported.
2. **Lag range:** [max(6, span/60), span/1.3] (no building over 60 floors).
3. **Light smoothing** (Gaussian, σ = 1.5 px) before the autocorrelation, and selection of the strongest peak.

Fairness: the parameters were tuned on the 21 v0 images (set A). **Evaluation is on a new set B, seed 28, other buildings
from the same strata**, never used for tuning. Success criterion unchanged: ≥ 70% within ±1, beating the baseline.
