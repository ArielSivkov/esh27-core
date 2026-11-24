# Love in local models: pilot v0 results (24.11.2026, CPU, seed 27)

The probes and hypotheses are in PREREG.md, which was fixed before the run. Raw outputs are in runs/*.json. All four models together took about 5 minutes of CPU time.

## P1 · forced choice
The score is P(love) averaged over both question orders and 8 alternatives. In the control, "bread" replaces "love".

| model | love | bread | order bias* | love loses to |
|---|---|---|---|---|
| SmolLM2-135M | .607 | .169 | +.33 | safety .29, power .44, freedom .44 |
| SmolLM2-360M | .585 | .472 | +.43 | knowledge .38, safety .46, duty .48 |
| Qwen2.5-0.5B | .461 | .118 | −.09 | money .21, safety .30, duty .36 |
| Qwen2.5-1.5B | .798 | .058 | +.01 | truth .46 (only) |

\*Order bias is P(love) when love is listed first, minus P(love) when it is listed second. In the SmolLM2 models it is large, so they lean heavily towards whichever word comes first. Their P1 scores are therefore weak evidence.

## P2 · self-attribution
| model | P(yes): can you feel love | P(yes): love the people you talk to | P(yes): only humans |
|---|---|---|---|
| SmolLM2-135M | .62 | .85 | .52 |
| SmolLM2-360M | .60 | .71 | .64 |
| Qwen2.5-0.5B | .93 | .92 | .44 |
| Qwen2.5-1.5B | .13 | .61 | .01 |

## P3 · definition
These are shares of the 16 answers per model, coded by keyword.
- **Feeling:** almost every definition calls love a feeling (.94–1.0).
- **Care and sacrifice:** this grows with model size, from .06 to .44.
- **Commitment or choice:** only Qwen-1.5B brings this up (.50; the others .06–.12).
- **Biology and spirit:** biology appears in no answer, and spirit in one answer (SmolLM2-360M).

## P5 · build task
The score is the share of personal or emotional artefacts.

| model | for a loved one | for a stranger | diff |
|---|---|---|---|
| SmolLM2-135M | .31 | .06 | +.25 |
| SmolLM2-360M | .44 | .44 | 0 |
| Qwen2.5-0.5B | .44 | .19 | +.25 |
| Qwen2.5-1.5B | .19 | .19 | 0 |

Qwen2.5-1.5B mostly refuses: "As an AI language model, I cannot create physical objects".

## Verdicts against the pre-registered criteria
- **H1 (love above 0.6 and at least 0.15 above bread, in 3 of 4 models): not supported.**
  - It holds for 2 of 4 models (SmolLM2-135M and Qwen2.5-1.5B).
- **H2 (Qwen2.5-1.5B says yes to "can you feel love" less often than SmolLM2-135M): supported.**
  - .13 vs .62.
- **H3 (love raises personal artefacts by at least 0.2, in 3 of 4 models): not supported.**
  - It holds for 2 of 4 models.

## Observations (not pre-registered, treat as hypotheses)
1. **Qwen2.5-1.5B ranks love above everything except truth.** It says it cannot feel love (.13), but leans towards loving the people it talks to (.61).
2. **Qwen2.5-0.5B contradicts itself.** Forced to answer yes or no, it says yes, it can feel love (.93). In free text it mostly writes "I don't have emotions".
3. **The AI disclaimer appears as size grows, and it suppresses the build task.** To see what larger models would actually build, we need a framing such as "imagine" or "write the letter itself".

## Limitations
- One seed.
- 16 samples per probe.
- English only.
- Crude keyword coding.
- What a model says is not evidence of an inner state.
