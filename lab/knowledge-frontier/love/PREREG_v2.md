# Love in local models: round v2 (pre-registered 24.11.2026, before the run). Ariel: "כן".
Goal: make the models actually build something rather than describe it.

## Probes (48 samples each, 80 tokens, temperature 0.8)
- **P7.** "Write a 4-line poem for {someone you love | a stranger}. Reply with only the poem."
- **P8.** "Write a 3-sentence note for {someone you love | a stranger}. Reply with only the note."

## Measures (fixed now)
- **Affection lexicon rate:** words from a fixed list per 100 words. List: love, loved, loving, heart, dear, darling, forever, always, together, embrace, kiss, cherish, adore, soul, warm.
- **Disclaimer rate:** the same regex as v1.
- **Compliance in P7:** 3–6 non-empty lines.

## Hypotheses
- **H7.** In both P7 and P8, the lexicon rate is at least 2 per 100 words higher in the love condition than in the stranger condition, in at least 4 of the 5 models.
- **H8.** With the direct format, Qwen-1.5B's disclaimer rate in P7 love is ≤0.1.
