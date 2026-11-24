# Tiny ladder: SmolLM2-135M-Instruct, Kaggle T4, 24.11.2026 00:45–02:43 UTC (~118 GPU-min)
Same frozen test set as SEAL (80 per task, excluded from training). Training: 10k exact-ground-truth examples per task, 2 epochs, full fine-tune, lr 1e-4.

| stage | mul | gcd | euler | betti | mean4 | control add (not trained) |
|---|---|---|---|---|---|---|
| 0 base | 0 | 0 | 0 | 0 | 0 | 0 |
| 1 answer-only FT | .263 | .825 | .988 | .988 | .766 | 0 |
| 2 scratchpad FT | .950 | .700 | .988 | .988 | **.906** | .312 |

For comparison, Qwen2.5-1.5B with SEAL (verifier-filtered self-training, no labels) reached .537.

Caveats:
- This is supervised training on exact labels, not self-improvement, so the two regimes differ.
- The test is in-distribution (same generators and ranges).
- Base 0 is partly a format failure.
- Scratchpad helped mul hugely (.26→.95) but hurt gcd (.83→.70). The long Euclid chains are a likely cause.
- Not yet tested: generalisation to longer numbers or bigger graphs, and a second seed.
