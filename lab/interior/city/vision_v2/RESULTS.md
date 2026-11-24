# City v2, a large quantized model: results (Kaggle T4×2, 2026-11-24, ~28 min wall × 2 GPUs)

[F] fact from `run_log_v2.txt` · [C] red-team computation · [H] hypothesis. Criteria are from PREREG.md, unchanged.
- [F] 47 of 53 images. The 32B-AWQ arm **failed to load**: `gptqmodel` was missing, an installation error on my side, not OOM.

| Arm | Floor consistency ±1 | 95% interval [C] | Street signs | Round-10 answers |
|---|---|---|---|---|
| 3B (v1) | 23/35 = 65.7% | 49–79% | 0/8 | n/a (not comparable) |
| 7B fp16 | 24/34 = 70.6% | 54–83% | 0/12 | 31.2% |
| 7B NF4 (quantized here) | 25/34 = 73.5% | 57–85% | 0/12 | 32.5% |

**Verdict after red team:**
- **No usable floor vote.**
  - 70.6% is one image above the bar, and its interval is ±15 points.
  - [C] 9 of the 24 agreements are the same round guess repeated (10,10 / 20,20). Exact agreement is 44%.
  - [C] 9 images were lost to cut-off output (160 tokens). Recovered from the raw text: 74–76%. The result moves with parsing.
  - There is no ground truth, so consistency ≠ accuracy. The 3B → 7B gain is within noise.
- **Quantization cost: 4-bit preserves the floor answers.**
  - fp16 vs NF4: 68/74 = 91.9% within ±1, with a lower bound of 83% [C], clearing the 80% bar.
  - [C] The text half of criterion 4 was never computed, so this is half-tested.
- **Street signs:** 0 in every arm.
- **Lessons for next time:**
  1. max_new_tokens ≥ 400, or a format that cuts off the text list.
  2. Install gptqmodel for AWQ.
  3. A ground-truth test set is required. The twin world can supply one (see davinci/).
