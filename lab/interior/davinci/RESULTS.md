# Da Vinci v0 / v0.1: results (2026-11-24, CPU only, renders from the twin world)

[F] fact from the result files · [H] hypothesis. Criteria are from PREREG.md (+A1), unchanged.

| Version | Set | Within ±1 floor | Baseline "always 4" | Excluded (frame/no period) | Verdict |
|---|---|---|---|---|---|
| v0 | A (21, seed 27) | 0/6 | 1/6 | 15 | fails |
| v0.1 | A (dev set, tuned) | 2/7 | 1/7 | 14 | not an evaluation |
| v0.1 | **B (20 new, seed 28)** | **5/13 (38%)** | **5/13** | 7 | **fails: below 70% and no better than the baseline** |

- [F] Set B has low-rise buildings only (f = 2–8). All 5 towers in the tiles were already used in set A.
- [F] The errors are mostly multiples of the period. One example: f = 8 → 2.0 (period 166 px, one "floor" per 4 actual floors).
  Another: f = 4 → 13.0 (period 11 px, window detail).
- [H] Finding the period from a single 1D profile is too weak. The window grid is a 2D pattern, and the vertical
  rhythm (floors) and horizontal rhythm (bays) have to be found together, after perspective rectification.
  That is the next step: rectification → 2D window-grid detection → floor/bay pitch, checked against the renderer.
- [F] Truth was taken as `f` from the tiles. Whether the facade engine draws exactly f floors was not checked independently;
  a threat to verify.
- Nothing goes into the world.

## v1: window detection with foundation models (Kaggle T4, ~1.5 GPU minutes)
| Arm | Within ±1 (21 fully in frame) | Towers (f ≥ 20) | Baseline "always 4" | Verdict |
|---|---|---|---|---|
| Grounding DINO | **11/21 = 52%** | 0/3 | 6/21 = 29% | **beats the baseline but below 70%; fails** |
| OWLv2 | failed: a transformers API change (my bug) | n/a | n/a | not run |

- [F] Low-rise (f = 2–4): mostly right. f = 8 → always 4 (3/3 undercount). Towers: it sees 2–34 windows, not hundreds.
- [H] Undercounting is a resolution problem: at 480×720 the windows of a distant building take a few pixels each.
  Next: slicing (SAHI-style) and zoom on the facade, plus fixing OWLv2. Still the best of the three methods
  (VLM 3B/7B: no truth; 1D rhythm: 38% = baseline).

## v3: lots of photos together, 14 Givat Yona photos (Kaggle T4, ~5 GPU minutes)
- [F] COLMAP: 7/14 images registered, mean reprojection 0.049 px, **but only 8 3D points** across 2 models.
  The criterion (≥ 6 registered, < 2 px) is met as worded, but **the result is degenerate**: 8 points are not a reconstruction,
  and the tiny reprojection error comes from having almost no points. I am reporting it as a **failure in substance**.
- [F] VGGT-1B: produced a cloud, but the 70th percentile of confidence = 1.0, the model's minimum. Most points are low confidence.
- [F] **Cross-check: median 117° (p90 168°) between COLMAP's and VGGT's relative rotations. Fails (criterion < 10°).**
  The two methods do not agree on the geometry.
- [H] The reason, by the file names (one spot on the hill, at 17:09–17:11, "panorama"): the photos were taken **from one
  standing point while turning**. A camera that only rotates has no parallax, so no method can produce depth from it.
  **Lesson for photographing:** for 3D, walk around the object and take a photo every 2–3 steps, with ~70% overlap between
  consecutive photos.

## v2: image → 3D (TripoSR, MIT), height = proportions × map width (Kaggle T4, ~14 GPU minutes for the successful run; 3 earlier install failures, ~3 minutes)
| Method | Within tolerance (3 m or 20%) of 21 | Median error |
|---|---|---|
| **TripoSR** | **4/21: fails** | 12.3 m |
| Image box ratio × map width (2nd baseline) | 14/21 (67%) | 2.6 m |
| "Always 13 m" | 6/21 | n/a |
- [F] The vertical axis was chosen without the truth (Pearson 0.78 with the box's pixel height).
- [F] TripoSR inflates heights on low buildings: 2 floors (6 m) → 8.5–19.3 m. It shrinks towers: 100 m → 79–86 m.
  **The 3D model adds nothing over the plain box ratio. A negative result.**
- [H] On renders the box ratio is partly circular (the box was projected from the true geometry), so its 67% is not
  evidence about real photos. On a photo the box has to be detected (segmentation), and that is the next test.
- 3D viewer: https://claude.ai/artifact/S7qxSEqLcSydqjjJi12NtB (private).
