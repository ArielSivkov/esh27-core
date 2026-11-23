# Experiment 1: what SEAL changes in the weights (pre-registration)

Written and committed **before** the run. Hypotheses and criteria are not edited after results arrive;
any later change goes in a dated "Amendments" section below, with the reason.

## Setup
- Model: Qwen2.5-1.5B-Instruct, fp32, Kaggle T4. Same loop as `lab/knowledge-frontier/seal/loop_sci_gpu2.py`
  (tasks mul, betti, euler, gcd; K=4; LoRA r=8, alpha=16, q_proj+v_proj; 3 rounds; same frozen set
  `frozen_sets_sci.json`). Differences, added only for this experiment: `torch.manual_seed(SEED)`, the LoRA
  init and the trained adapter are saved every round, and the original q/v weights W0 are kept for analysis.
- Two SEAL seeds: 27 (the run that earlier gave gcd .175 → .887) and 28.
- Two control adapters, each trained once from the **base** model, same hyperparameters:
  - `ctrl_add`: the base model's own verifier-passed answers to 3-digit addition, with N = SEAL seed-27 round-1 kept count.
    It asks whether the layer/direction profile is specific to the task, or generic to "LoRA on this prompt format".
  - `ctrl_shuf`: the seed-27 round-1 kept questions with their answers permuted among themselves (wrong labels, same format,
    same N). It asks whether the profile needs correct answers.
- Each round's ΔW = (alpha/r)·B·A per layer and module (28 layers × {q, v} = 56 modules).

## Measurements (per module)
1. ‖ΔW‖_F and the relative ‖ΔW‖_F / ‖W0‖_F.
2. Effective rank (Roy & Vetterli: exp of the entropy of normalized singular values), max 8.
3. Similarity between adapters: (a) cosine of flattened ΔW; (b) output-side subspace overlap: ‖U1ᵀU2‖²_F / k with the top
   k=4 left singular vectors (random expectation k/d_out); (c) the same on the input side (right singular vectors).
4. Direction relative to W0: the fraction of ‖ΔW‖² inside the top 5% left (output) singular subspace of W0, divided by
   0.05 (1 = no preference). The same on the input side.
5. How far LoRA A moved from its init: ‖A − A_init‖ / ‖A_init‖.

## Hypotheses and success criteria (fixed)
- **H1, concentration.** The 7 of 28 layers (top quarter) with the largest ‖ΔW‖² (q+v) hold ≥ 50% of the total ‖ΔW‖².
  Uniform would be 25%. Supported if true in ≥ 2 of 3 rounds in **both** seeds.
- **H1s, specificity of the profile.** Spearman ρ of the 28-layer ‖ΔW‖² profile: seed 27 R1 vs seed 28 R1 > 0.7, **and**
  seed 27 R1 vs `ctrl_add` < 0.5. If both correlations are high, the profile is generic to LoRA on this format and says
  nothing about the task (reported as a negative result).
- **H2, low rank.** Median effective rank over the 56 modules of SEAL R1 (both seeds) < 4.
- **H3, a stable direction.** Mean output-side overlap between consecutive SEAL rounds (R1-R2, R2-R3, both seeds)
  is ≥ 5× its random expectation, **and** greater than the mean overlap of SEAL R1 with `ctrl_add`.
- **H4, direction relative to W0** (three outcomes fixed in advance): mean output-side ratio over modules (SEAL R1, both seeds)
  > 2 → "the update amplifies directions W0 already uses"; 0.5–2 → "no preference"; < 0.5 → "new directions".

## Known threats, checked before any claim
- **LoRA A init artifact.** A starts random and moves little, so the input side of ΔW ≈ a random 8-dim subspace. Full-matrix
  cosine and input-side overlap between independent runs will be near 0 even if the function learned is the same.
  That is why H3 uses the output side. Input-side numbers are reported, but no claim rests on them.
- **Amount of training.** Kept counts grow per round (more steps → bigger norm). Norms are compared within a round, and
  across rounds only per step.
- **Weight size.** Raw ‖ΔW‖ may track ‖W0‖. The relative norm is reported, and its layer profile is checked against the raw one.
- **Generic LoRA dynamics.** Covered by the `ctrl_add` / `ctrl_shuf` controls.
- **n.** Two seeds per condition is small. All conclusions are labeled with it.

## Amendments
(none yet)
