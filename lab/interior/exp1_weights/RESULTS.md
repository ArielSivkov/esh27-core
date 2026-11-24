# Experiment 1: results (v1, Kaggle T4, 2026-11-24, 21 min GPU)

Labels: **[F]** fact from the run log (`results/run_log_v1.txt`) · **[C]** computation · **[H]** hypothesis.
Open model only (Qwen2.5-1.5B-Instruct). Nothing here is a claim about any other model.

## Behaviour (reproduces the earlier result)
- [F] Base is identical to the earlier runs: gcd .175, mean .2906, ctrl (addition) .9875.
- [F] Seed 27: gcd .575 → .80 → .8625, mean .384 → .475 → .522, all promoted, ctrl flat .9875.
  The earlier run gave .887; this run differs from it only in `torch.manual_seed`.
- [F] Seed 28: gcd .65 → .8625 → .8875. R3 was **rejected** (mean +0.00 < +0.03). Ctrl flat.
- [F] Controls. `ctrl_add` (N=111): no effect on the tasks, mean .272, with last-batch loss 0.000 (the base already knew
  this data). `ctrl_shuf` (wrong answers): breaks the model, mean .009, ctrl 0.0.

## Pre-registered verdicts (thresholds unchanged)
| | Criterion | Result | Verdict |
|---|---|---|---|
| H1 concentration (weight norm) | top-quarter share ≥ .5 | .29–.34 (uniform .25) | not supported |
| H1s specificity | seed-ρ > .7 and ctrl-ρ < .5 | .59 / .07 | not supported |
| H1f concentration (functional) | ≥ .5 in 2/3 rounds | .42–.50 | not supported |
| H2 low rank | median erank < 4 | 7.09 of 8 | not supported |
| H3 stable direction | ≥ 5× random and > ctrl | 7.3×, .066 > .036 | **passes as written**, but see red team |
| H4 direction vs W0 | ratio band | 1.19 | "no preference" |

## Red team (separate agent, `redteam/`)
1. **The weight measures are blind here.** [C] In a toy run of AdamW with LoRA B=0 for 28–50 steps:
   - a strong rank-1 signal still gives erank ≈ 5.9;
   - a 10× gradient spread across layers still gives a top-quarter share of 0.254.

   [F] The q/v energy split (.853–.867) equals the parameter-count ratio (.857) for every adapter, controls included.
   So H1 and H2 do not "fail" because of anything SEAL did. The measures cannot tell at this training length.
2. **H3's pass mixes two scales.** [C] Per module, against random:
   - consecutive SEAL rounds: q 29×, v **3.6×**;
   - control vs control: q 18×, v 1.3×.

   Any LoRA clears 5× on q, and SEAL fails it on v. The excess over the generic baseline is only about 1.6× (q) and 2.7× (v).
   [F] The overlap decays: R1–R3 and cross-seed R3 are back at the ctrl_shuf level. [H] Most of the shared direction
   comes from shared data and the shared base model, not from a mechanism that builds up over rounds.
3. **The selectivity measure (≈1.0) is not evidence.** [C] About 75% of the tokens in the gcd and addition prompts are
   identical, and the measure uses prompt tokens only, not the answer position.
4. **Gaps.**
   - The analysis files (analysis.json, history.json with kept_by_task) and the adapters were not downloaded,
     because the environment proxy blocks `www.kaggleusercontent.com`. Only the log was read.
   - ctrl_add is a weak control (near-zero loss).
   - The analysis includes the rejected s28_r3.
   - n = 2 seeds.

## Conclusion
- **[F/C] The run is a negative, methodological result.** Weight-level statistics of a LoRA trained with Adam for 28–50 steps
  (norm per layer, effective rank, q/v split) are fixed by the optimizer. They cannot show where SEAL changed the model.
- The only signal above the controls is a small excess of shared output direction on q_proj (≈1.6×) and v_proj (≈2.7×).
  It fades by round 3.
- [H] To locate the change, the next step should measure behaviour, not weights:
  1. per-layer adapter ablation on the frozen gcd set, which measures accuracy loss when one layer's ΔW is removed;
  2. functional effect at the answer position;
  3. logit lens (experiment 2).
