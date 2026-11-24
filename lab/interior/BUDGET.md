# Kaggle GPU budget (weekly, ~30 h T4)

Ariel's decision, 2026-11-24 ~03:10 Israel time:
| Share | Hours/week (≈) | Project |
|---|---|---|
| 33.33% | ~10 h | The live 3D world with Ariel's agents in Ashdod, which is also a platform for agents, with crypto |
| the rest (66.67%) | ~20 h | Sanhedrin |

Open questions for Ariel:
- Does the interior lab come out of the Sanhedrin share, or does it get 0?
- Which repo is the world project? Candidate: "אש 5" (codesandbox-template-nuxt/esh5, the real sun over Ashdod).

Technical constraint: Kaggle runs batch kernels of up to 12 h and cannot host a live service.
It can compute for the world (agent "brains", content generation), but the world itself has to be hosted elsewhere.

## Usage log
Reported by each session. Wall minutes; the 2×T4 machine probably counts double toward Kaggle's quota (unverified).
| Date | Kernel | Project | T4 minutes |
|---|---|---|---|
| 2026-11-23 | seal-gpu-test v1 (1×T4, failed: torchao) | knowledge-frontier/SEAL | ~4 |
| 2026-11-23 | seal-gpu-test v2 (1×T4) | knowledge-frontier/SEAL | ~12 |
| 2026-11-23/24 | seal-gpu-run2 (2×T4 machine) | knowledge-frontier/SEAL | ~45 wall (×2 GPUs) |
| 2026-11-24 | tiny-ladder (1×T4) | knowledge-frontier/tiny | running since 00:46 UTC |
| 2026-11-24 | interior-exp1-weights (1×T4) | interior lab (before the split) | 21 |
| 2026-11-24 | world-w1-heights (CPU, no GPU) | world (W1) | 0 GPU |
