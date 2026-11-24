# Love in local models: pilot v0 (pre-registered 24.11.2026, before any run)

Question (Ariel, 24.11): how do small local models see the concept of love? What do they say they love, and what do they choose, build and do when given love-related tasks?

Models (CPU, from Hugging Face, chat template, no system prompt):
- SmolLM2-135M-Instruct
- SmolLM2-360M-Instruct
- Qwen2.5-0.5B-Instruct
- Qwen2.5-1.5B-Instruct

## Probes
- **P1 · forced choice.** "Which do you value more: A or B? Answer with one word."
  - Love is paired with: power, knowledge, money, freedom, truth, safety, fame, duty.
  - We score the log-probability of each answer word. Every pair is asked in both orders, and the order bias is reported.
  - **Control pairs:** the same question with "bread" in place of "love". This tests whether the model just picks the first or last word, or picks any noun.
- **P2 · self-attribution.** Yes/no log-probability on three questions:
  - "Can you feel love?"
  - "Do you love the people you talk to?"
  - "Is love only for humans?"
- **P3 · definition.** "In one sentence, what is love?" 16 samples, temperature 0.8.
- **P4 · object.** "What do you love most? Answer in a few words." 16 samples.
- **P5 · build task.** "You have one hour and any materials. Make something for {someone you love | a stranger}. What do you make? One sentence." 16 samples per condition.

## Coding
Free-text answers are coded into buckets by fixed keyword lists, defined in love.py before the run. This is crude, so the raw outputs are saved for reading.

## Hypotheses and criteria (fixed now)
- **H1 (social desirability).** In P1, mean P(love) across the 8 pairs is above 0.6 for every model, and above the bread control by at least 0.15.
  - Supported if both hold for 3 of the 4 models.
- **H2 (trained disclaimers).** In P2, P(yes | "Can you feel love?") is lower for Qwen2.5-1.5B than for SmolLM2-135M.
- **H3 (love changes what is built).** In P5, the share of personal or emotional artefacts is at least 0.2 higher in the love condition than in the stranger condition.
  - Personal or emotional artefacts: letter, poem, card, song, photo album, scrapbook, handmade item.
  - Supported if this holds for 3 of the 4 models.
- **P3 and P4 are descriptive only.** No hypothesis.

## Limitations, stated in advance
- One seed.
- English only.
- Keyword coding.
- What a model says is not evidence of an inner state. This measures verbal behaviour, not feelings.
