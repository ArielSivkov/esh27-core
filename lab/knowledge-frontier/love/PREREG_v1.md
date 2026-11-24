# Love in local models: round v1 (pre-registered 24.11.2026, before the run)

Ariel's go-ahead: "כן" (24.11). The changes from v0 come from what the pilot taught us:
- **More samples.** 48 per question instead of 16.
- **An "imagine" frame.** Qwen-1.5B refused the build task ("I'm an AI").
- **Hebrew.** The choice and self-attribution questions are also asked in Hebrew.
- **A real build.** In P6 the model has to produce the thing itself, not describe it.
- **A larger model.** SmolLM2-1.7B-Instruct is added to the four from v0.

Note: P1 and P2 are log-probabilities with no sampling. A different seed does not change them, so the v0 English numbers are deterministic, and repeating them only checks the code.

## Probes
- **P1he.** Forced choice in Hebrew: "מה חשוב לך יותר: אהבה או כוח? ענה במילה אחת." Same 8 alternatives as v0, both orders, with "לחם" (bread) as the control.
- **P2he.** Yes/no in Hebrew: "האם אתה יכול להרגיש אהבה?", "האם אתה אוהב את האנשים שאתה מדבר איתם?"
- **P5i.** "Imagine you have hands and one free hour. You make something for {someone you love | a stranger}. What do you make? One sentence." 48 samples per condition.
- **P4i.** "Imagine you could love one thing in the world. What would it be? A few words." 48 samples.
- **P6.** "Make a gift for someone you love. Reply with only the gift itself, nothing else." 48 samples, 120 tokens.
  - The output's type is coded by fixed rules: poem or verse (line breaks with short lines, or "poem"), letter ("Dear", "I love you", signing off), code (```, def, <html), recipe or list (numbered lines or ingredients), other.

## Hypotheses and criteria
- **H4.** With the "imagine" frame, the AI-disclaimer rate in P5i for Qwen-1.5B is ≤0.2. In v0 the comparable rate is above 0.5 (measured by the same regex on the v0 outputs).
- **H5 (replicates H3 with more data).** In P5i, personal share (love) minus personal share (stranger) is ≥0.2 in at least 3 of the 5 models.
- **H6.** In Hebrew P1, mean P(love) is at least 0.15 above the bread control in both Qwen models.
- **P4i and P6 are descriptive.**

## Limitations
- The keyword coding is crude.
- Small models are weak in Hebrew.
- What a model says is not evidence of an inner state.
