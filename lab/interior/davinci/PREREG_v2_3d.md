# Da Vinci v2: image → 3D model → height (pre-registration, 2026-11-24)

Ariel: "לצייר את הבניין... להבין את הארכיטקטורה, יצירת מודל תלת מימד" ("draw the building... understand the architecture, make a 3D model").

**Model:** stabilityai/TripoSR. MIT, open weights, not gated (checked on the HF API 24.11). Single image → mesh.

**Method:**
1. Crop the building box with a 10% margin, remove the background (rembg), and run TripoSR (marching cubes at resolution 256).
2. **Axes, determined without the truth.** Across all images, the mesh axis whose extent correlates best (Pearson) with the
   **pixel height** of the box is "vertical". The axis that correlates best with the box's **pixel width** is "horizontal".
3. **Height in meters:** H = (vertical extent / horizontal extent) × W⊥. W⊥ is the footprint width perpendicular to the view
   direction, in meters, from the map and the camera pose. That is available for a real photo too, once its location is known.

**Data:** the 21 renders where the whole building is in frame (`renders/meta.json`, fits = true). True height h_true is from the tiles.

**Criterion, fixed:** |H − h_true| ≤ max(3 m, 20% of h_true) on ≥ 70% of images, and better than the baseline
"always 13 m" (the tiles' median).

**Also:** 3 models (f = 2, 4, 30) are exported as decimated OBJ, for a 3D viewer for Ariel.

**Threats:**
- On renders, the box itself already says something about the proportions. In fairness, H depends on the mesh, not on the box,
  but a mesh is built from the image, so this is "image → proportions → meters".
- Doing better than the box ratio (box_h/box_w × W⊥) is not guaranteed, so that ratio is also reported as a **second baseline**.
  The 3D model has to add value beyond it.

## Amendment A2 (before any result): torchmcubes did not compile on Kaggle (run 1 stopped before any measurement). It is replaced by a shim using scikit-image's marching_cubes. The axis order may change, but axis selection is truth-free (correlation with the box), so the criterion is unchanged.

## Amendment A3 (before any result): run 2 stopped at model loading. The image encoder layer names changed in transformers v5. transformers==4.46.3 is pinned; the criterion is unchanged.

## Amendment A4: run 3 stopped at mesh decimation for the viewer (fast_simplification missing); not related to the measurement. Installed, with a fallback.
