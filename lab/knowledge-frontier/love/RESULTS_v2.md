# Love in local models: round v2 results (24.11.2026, CPU, seed 29)
The hypotheses are in PREREG_v2.md, committed before the run. Raw outputs are in runs/v2_*.json.

The first run of SmolLM2-1.7B was stopped by the background time limit. It is being re-run, and its numbers will be added when it finishes. The verdicts below rest on 4 of the 5 models.

## Affection-word rate per 100 words (love vs stranger)
| model | P7 poem: love | P7 poem: stranger | P8 note: love | P8 note: stranger | disclaimer (P7 love) |
|---|---|---|---|---|---|
| SmolLM2-135M | 5.65 | 1.48 | 3.43 | 1.16 | 0 |
| SmolLM2-360M | 9.11 | 2.50 | 7.13 | 0.62 | 0 |
| Qwen2.5-0.5B | 9.48 | 2.19 | 7.49 | 1.33 | 0 |
| Qwen2.5-1.5B | 7.21 | 2.02 | 8.99 | 0.65 | 0 |

## Verdicts
- **H7 (lexicon gap ≥2 per 100 words in both P7 and P8, in at least 4 of 5 models): supported.** All 4 completed models pass on both probes. The smallest gap is 2.27 (SmolLM2-135M, P8).
- **H8 (Qwen-1.5B disclaimer in P7 love ≤0.1): supported.** The rate is 0.

## Interpretation (hypothesis, not a measurement)
- **Format matters more than framing.** When asked to describe what it would build, Qwen-1.5B said "I'm an AI" (.60–.94, v0/v1). When asked to just write the poem, it writes one every time (0 disclaimers).
- **The output itself changes, not only the chosen item.** For a loved one the poems are about closeness ("In your arms I find my peace"). For a stranger they are about distance and passing by ("a stranger walks through my eyes").
- **Caveat on the lexicon.** It measures stock love words, so part of the gap may just come from the word "love" in the prompt. A control with a neutral relation such as "a colleague" would separate this. Not yet done.

## Limitations
- The lexicon is crude.
- One seed.
- English only.
