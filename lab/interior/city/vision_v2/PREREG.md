# City v2: a large model, quantized (pre-registration, 2026-11-24)

Ariel: "בואו נעשה quantization למודל גדול" ("let's quantize a big model"). From the world's third of the Kaggle budget.
Same data, same two wordings, same criteria as v1 (`../vision_v1/PREREG.md`), so the result is directly comparable to 3B
(v1: floor consistency 65.7%, street signs 0/8).

Arms, all in one kernel (T4×2 machine). Images are downloaded once with backoff and reused by every arm.
- **A:** Qwen2.5-VL-7B-Instruct, fp16, `device_map=auto` across 2 GPUs.
- **B:** the same 7B in 4-bit NF4 (bitsandbytes, quantized here), on 1 GPU.
- **C:** Qwen2.5-VL-32B-Instruct-AWQ (pre-quantized to 4-bit), `device_map=auto`. If it fails to load or OOMs, it is reported
  as failed, not hidden.

Criteria (unchanged from v1):
1. Floor self-consistency within ±1 between the two wordings ≥ 70% → usable as one vote.
2. Street-sign check: the share of Hebrew readings that match the catalog street.
3. Floor coverage.

New, fixed in advance:
4. **The cost of quantization:** agreement between A and B on floors (±1), and on whether street-like Hebrew text was read.
   ≥ 80% → "4-bit preserves behavior on this task"; otherwise "quantization changes the answers".
5. **Round-number spike:** the share of floor answers that are multiples of 10. v1 had 18/37. A drop is a sign of
   counting rather than guessing.

There is still no ground truth for floors on these photos, so consistency ≠ accuracy. Nothing goes into the world.
