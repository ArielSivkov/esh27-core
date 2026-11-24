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
