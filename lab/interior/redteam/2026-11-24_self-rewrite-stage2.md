# Red team: self-rewrite lab, stage 2 ("self-edits do not help"), 2026-11-24

Target: hello-world @ ccr-9546e606-71iydo, self-rewrite-lab/selfloop/RESULTS-stage2.md (commit 044198f).
Read-only review by a separate agent. Nothing was run on GPU. [F] fact · [C] computation · [H] hypothesis.

1. **Headline numbers reproduce. Holds.**
   - [C] Recomputed from the log.json files:
     - self−anchor2 at c0: +0.0222, +0.0237, +0.0205 (seeds 0/1/2).
     - self−fake at c0: +0.0315, +0.0309, +0.0273.
     - The c4 values match the results file.
   - [F] The CIs cannot be rechecked, because scores_*.npz is not in git.
   - [F] Error in RESULTS: selfraw had **cycles 2 and 3** rejected, not only cycle 2.
2. **Fairness. Weakened for selfraw, holds for self.**
   - [C] Characters are matched (~26–28k per week), but self and fake train on 40 items against 20 for raw, so they get about
     twice the optimizer steps.
   - [F] Criterion 5, the step-matched raw control, was never run.
   - [F] At c4, selfraw starts from adapter_1 and anchor2 from adapter_3, so selfraw's c4 deficit comes mostly from the gate.
     At c0–c1 it ties anchor2 (−0.004, +0.0005).
   - [C] self is worse before any gate (c0), and worse than its own incumbent in every cycle.
   - [F] No leakage found.
3. **Validity. Weakened.**
   - [H] The test is next-week perplexity, not SEAL's QA on the passages trained on.
   - [F] self's train loss is 1.6–1.9 against raw's 3.4, and the self-edits are repetitive, so the model is collapsing toward its own text.
   - Supported claim: "135M self-edits hurt next-week perplexity". Not: "SEAL does not help".
4. **Pre-registration. Weakened.**
   - [F] Criterion 1 needs 2 of 3 seeds, but selfraw ran on 1 seed.
   - [F] Criterion 5 was skipped, no cycle was pre-named, and anchor2 was substituted for anchor.
   - [F] The "seeds" share the same data.
   - [F] No thresholds were moved.
5. **CI method. Holds.**
   - [F] The pairing is valid. There is no multiple-comparison correction, and the bootstrap ignores seed variance.
   - [C] The self effect has z ≈ 6 and survives a Bonferroni correction over ~20 tests.

**Caveats the result must carry**
1. Only the self result is robust. For selfraw, the right verdict is "no evidence of help", not "worse".
2. A 135M model, 20 docs per week, no step-matched control: this says nothing about SEAL at 1–7B.
