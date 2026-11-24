# D1: inside da Vinci, what TripoSR knows and what it relies on (pre-registration, 2026-11-24)

Ariel: "תעשה עליו ניסויים במעבדה" ("run experiments on it in the lab"). The background is v2's failure: TripoSR inflates low buildings and shrinks towers.

**Data:** twin-world renders where the whole building is in frame: sets A+B (21) plus a new set C (seed 29, f ∈ {1,2,3,4,8}, 62 buildings,
framing as in B). The crop and background removal are identical to v2.

## H1: does height exist inside? (a linear probe)
- Features: the hidden states of the image encoder inside TripoSR (`image_tokenizer`, a DINO ViT), per layer, mean-pooled over patches.
- Target: log(f) (floors).
- Probe: ridge (α chosen by inner CV over {0.1, 1, 10, 100}), **leave-one-out**, R² on the held-out samples.
- **Null:** the same probe on randomly shuffled labels, 200 permutations per layer. The threshold is the null's 95th percentile.
- **Criterion:** at the best layer, R² > 0.5 **and** above the null threshold.
- **Second control:** a probe on simple features only (the image box aspect ratio and the building's pixel area).
  If it gets ≈ the same R², the encoder has nothing beyond proportions (the "image size" threat, as in the lab rules).

## H2: what does the 3D rely on? (a causal intervention)
- Stretch the input crop vertically by s ∈ {0.8, 0.9, 1.1, 1.25} (width unchanged), on 15 buildings from set C (a fixed choice, seed 29).
- Measure: the mesh's (vertical extent / horizontal extent) ratio.
- Elasticity = the slope of log(ratio) against log(s).
- **Fixed in advance:**
  - 0.5–1.5 → "the model copies the image's proportions";
  - < 0.3 → "it ignores them (it has a prior of its own)";
  - in between → "partial".

## H3: where does the inflation come from? (descriptive)
Correlation of v2's error (log H/h) with: box aspect, pixel area, distance, and f. No criterion.

Small n (≈ 60–80); the results are a direction, not a law. Red team before the report.
