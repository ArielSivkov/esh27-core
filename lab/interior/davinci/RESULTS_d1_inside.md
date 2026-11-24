# D1: inside da Vinci (TripoSR). Results (Kaggle T4, ~75 GPU minutes; the premature v1 run was not read)

[F] fact from `run_log_d1_inside.txt` · [C] red-team / my computation · [H] hypothesis. Criteria are from PREREG_d1_inside.md.

## H1: does height exist inside the image encoder? **Supported as worded, weaker than it looks**
- [F] R² by layer (LOO ridge, n = 62): 0.00 (layer 0) → 0.39 → 0.48 → 0.60 → … → **0.735 (layer 8, the peak)** → 0.64 (layer 11).
  The permutation null's 95th percentile is between −0.12 and −0.05 at every layer. Above 0.5 and above the null: passes the criterion.
- [F] The simple-feature control (log box aspect + log pixel area) gets R² = 0.747, the same as the encoder.
- [C] Equal R² does not show the encoder has "nothing more". The test needed is whether encoder + box beats box alone, and it was not run.
  Pixel area comes from the uncropped image, which the encoder never sees.
- [C] The 3 towers are 5% of the samples but carry 39% of the variance. Without them the simple control drops to 0.686.
  The encoder R² without them is unknown (features were not saved).
- [H] The layer shape (a rise to the middle-upper layers, a small drop at the end) is typical of ViT probes, but n = 62.

## H2: what does the 3D rely on? **"Copies the image's proportions"**, but this is partly built in
- [F] Median elasticity 0.904 (IQR 0.475–1.07), 15 buildings. In the pre-registered band (0.5–1.5).
- [C] **Axis bug, found by the red team.**
  - Mesh axis 1 is pinned at ≈1.0 in every row: that is the image width, fixed by resize_foreground.
  - Axis 2 is a **depth** that the model invents.
  - v2 picked "horizontal" = axis 2, by a weak correlation (r = 0.128), and D1 reused that pick.
  - With the correct axes (0/1), the elasticity is 0.96 (IQR 0.90–0.99). The 2 negative slopes are depth jumps (an artifact).
- [C] Since the width is pinned, an elasticity of ≈ 1 is close to automatic. This measures **silhouette fidelity**, not "lack of architectural knowledge".

## Correction to v2 (same data, no new run)
| v2 | Within tolerance (of 21) | Median error | Median log(H/h) |
|---|---|---|---|
| As run (height ÷ depth): the bug | 4 | 12.3 m | +0.84 (inflation ×2.3) |
| **Corrected (height ÷ width)** | **11** | **3.2 m** | **+0.22** |
| Box ratio (baseline) | 14 | 2.6 m | n/a |
- "Inflating low buildings" was mostly **my bug**, not the model's. Corrected, TripoSR still fails (11/21 < 70%) and is still no better than the box,
  with a remaining +22% bias.

## Lessons
1. Determining axes by weak correlation is dangerous. A dimension pinned by preprocessing has to be checked first.
2. Next probe: encoder + box against box alone (incremental R²), saving the features, and without the towers.
