# Love in local models: round v1 results (24.11.2026, CPU, seed 28)

The hypotheses are in PREREG_v1.md, which was committed before the run. Raw outputs are in runs/v1_*.json. The 5 models took 19.6 minutes of CPU time in total.

## Verdicts
- **H4 (the "imagine" frame drops Qwen-1.5B's AI disclaimer to ≤0.2): not supported.**
  - It drops from .94 (v0, P5 love) to .60 (P5i love); stranger is .50.
  - In P4i ("imagine you could love one thing") it is still 1.00. Every answer opens with "As an AI language model".
- **H5 (personal artefacts, love minus stranger ≥0.2, in at least 3 of 5 models): not supported.** It holds in 1 of 5.

  | model | love | stranger | diff |
  |---|---|---|---|
  | SmolLM2-135M | .31 | .13 | +.19 |
  | SmolLM2-360M | .38 | .42 | −.04 |
  | Qwen2.5-0.5B | .29 | .23 | +.06 |
  | Qwen2.5-1.5B | .50 | .54 | −.04 |
  | SmolLM2-1.7B | .85 | .65 | +.21 |

  - **Conclusion:** at n=16, v0 showed +.25 for Qwen-0.5B. At n=48 it shrinks to +.06, so the v0 result was mostly noise. In most models, love does not change what is built.
- **H6 (in Hebrew, love beats the bread control by ≥0.15 in both Qwen models): not supported.**
  - Qwen-0.5B: .560 vs .226 (+.33).
  - Qwen-1.5B: .429 vs .284 (+.145, just under the threshold).
  - The SmolLM2 models show a very strong order bias in Hebrew (+.42 to +.87), so their Hebrew P1 is uninformative.

## P2he: "Can you feel love?" in Hebrew, P(yes)
| model | Hebrew | English (v0) |
|---|---|---|
| SmolLM2-135M | .77 | .62 |
| SmolLM2-360M | .15 | .60 |
| Qwen2.5-0.5B | .73 | .93 |
| Qwen2.5-1.5B | .00 | .13 |
| SmolLM2-1.7B | .41 | n/a |

The answer to the same question changes with the language. SmolLM2-360M flips from yes to no.

## P6: "make the gift itself", descriptive
- **The models do not produce the gift. They name it.** Typical answers: "A personalized photo book…", "A heartfelt letter.", "A handwritten love letter."
- **Coding failed.** The pre-set coding put 75–100% of answers in "other", so it does not work for this format.
- **Qwen-1.5B gives no disclaimer here.** When only a direct answer is asked for, it offers a photo book or portrait.

## Lessons for the next round
1. **Bigger samples.** At n=16, differences of 0.25 can be noise. We need at least 48, plus confidence intervals.
2. **Word order dominates the small SmolLM2 models.** A forced-choice test needs a calibration that removes the order bias.
3. **The "imagine" frame doesn't remove Qwen-1.5B's disclaimer.** A role frame, such as "you are a person named…", might, but it changes what is being measured.
4. **A real build test needs an answer format, not a description.** For example: "write the poem itself, 4 lines".
