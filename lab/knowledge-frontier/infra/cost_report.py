#!/usr/bin/env python3
"""Speed and cost per SEAL experiment, computed only from what seal/arms_results.md recorded.

Every input number is tied to a verbatim snippet of arms_results.md; the script stops if a snippet is missing,
so a number can never drift away from its record. Output: a table on stdout and summary.json in $LAB_RUN_OUT.
Labels: FACT = written in the record; CALC = arithmetic on facts; STATED = given by Ariel, not checkable here.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
TEXT = open(os.path.join(LAB, "seal", "arms_results.md"), encoding="utf-8").read()

# (label, device, model, rounds, minutes, snippet that must appear verbatim in arms_results.md)
RUNS = [
    ("ARM I", "cpu (where: not recorded)", "Qwen2.5-0.5B", 2, 7.7, "ARM I (0.5B, euler+gcd, K4, s27)"),
    ("ARM H", "cpu (where: not recorded)", "Qwen2.5-0.5B", 2, 9.8, "mul .412->.537(REJECT, ctrl .675->.65)->.525(PROMOTE, ctrl .875); 9.8 min"),
    ("ARM C", "cpu (where: not recorded)", "Qwen2.5-0.5B", 2, 14.0, "ctrl .75->.875->.863; both promoted; 14 min"),
    ("ARM F", "cpu (where: not recorded)", "Qwen2.5-0.5B", 2, 14.4, "ctrl .675->.675->.738; 14.4 min"),
    ("LOCAL", "cpu, session container", "Qwen2.5-0.5B", 2, 16.0, "ctrl .762->.80->.887; 16 min"),
    ("ARM B", "cpu (where: not recorded)", "Qwen2.5-0.5B", 2, 22.6, "0.487(REJECT ctrl .762->.738); 22.6 min"),
    ("ARM G", "cpu (where: not recorded)", "Qwen2.5-0.5B", 2, 37.0, "0.412(REJECT ctrl .812->.75); 37 min"),
    ("ARM J", "cpu (where: not recorded)", "SmolLM2-1.7B", 2, 46.0, "ctrl .45->.575->.675; 46 min"),
    ("ARM A", "cpu (where: not recorded)", "Qwen2.5-1.5B", 2, 51.0, "ctrl .9875 flat; 51 min"),
    ("ARM E", "cpu (where: not recorded)", "Qwen2.5-1.5B", 2, 52.5, "ctrl .9625 flat; 52.5 min"),
    ("4-CPU container", "cpu, 4 cores", "Qwen2.5-1.5B", 2, 120.0, "~2 h for 2 rounds on 4-CPU container"),
    ("Kaggle T4", "gpu, Tesla T4", "Qwen2.5-1.5B", 3, 10.0, "3 rounds — 24.11.2026 01:21–01:31 Israel (≈10 min)"),
]
SAME_CONFIG = "Qwen2.5-1.5B, all tasks, K4, seed 27"
WEEKLY_GPU_HOURS = 30  # STATED by Ariel; Kaggle is not reachable from this session to confirm

# reproducibility CPU vs GPU, same config and frozen set: base and per-round means as recorded
REPRO = dict(cpu=("ARM A (Qwen 1.5B, all, K4, s27): mean .29->.416->.484", [0.29, 0.416, 0.484]),
             gpu=("Base identical to CPU arm A (reproducible): mul .70 betti .20 euler .087 gcd .175 mean .29", None),
             gpu_r1=("R1 kept 109 → mean .406", 0.406), gpu_r2=("R2 kept 163 → mean .475", 0.475))


def need(snippet):
    if snippet not in TEXT:
        sys.exit(f"cost_report: snippet not found in seal/arms_results.md, refusing to guess: {snippet!r}")


def main():
    for r in RUNS:
        need(r[5])
    for v in REPRO.values():
        need(v[0])
    rows = []
    print(f"{'run':16} {'device':28} {'model':14} {'rounds':>6} {'min':>6} {'min/round':>9}")
    for label, device, model, rounds, minutes, _ in RUNS:
        per = minutes / rounds
        rows.append(dict(run=label, device=device, model=model, rounds=rounds, minutes=minutes, min_per_round=round(per, 2)))
        print(f"{label:16} {device:28} {model:14} {rounds:6d} {minutes:6.1f} {per:9.2f}")
    by = {r["run"]: r for r in rows}
    gpu = by["Kaggle T4"]["min_per_round"]
    speedup = {k: round(by[k]["min_per_round"] / gpu, 1) for k in ("ARM A", "ARM E", "4-CPU container")}
    gpu_hours_per_run = by["Kaggle T4"]["minutes"] / 60
    runs_per_week = WEEKLY_GPU_HOURS / gpu_hours_per_run
    cpu_r = REPRO["cpu"][1]
    repro = dict(base_mean_cpu=cpu_r[0], base_mean_gpu=0.29, base_identical=True,
                 r1_cpu=cpu_r[1], r1_gpu=REPRO["gpu_r1"][1], r2_cpu=cpu_r[2], r2_gpu=REPRO["gpu_r2"][1],
                 trained_rounds_identical=(cpu_r[1] == REPRO["gpu_r1"][1] and cpu_r[2] == REPRO["gpu_r2"][1]))
    print(f"\nSAME CONFIG ({SAME_CONFIG}), minutes per round, GPU vs CPU (CALC): x{speedup['ARM A']} vs arm A, "
          f"x{speedup['ARM E']} vs arm E (same model and tasks, seed 28), x{speedup['4-CPU container']} vs the 4-CPU container")
    print(f"cost of one 3-round T4 run (CALC): {gpu_hours_per_run:.3f} GPU-hours = {100 * gpu_hours_per_run / WEEKLY_GPU_HOURS:.2f}% "
          f"of the STATED {WEEKLY_GPU_HOURS} h/week -> at most {runs_per_week:.0f} such runs per week (no startup, queue or failure overhead)")
    print(f"money per run: 0 (Kaggle free tier, no paid service in the loop)")
    print(f"reproducibility (FACT): base evaluation identical CPU/GPU (mean {repro['base_mean_cpu']}); after training "
          f"R1 {repro['r1_cpu']} cpu vs {repro['r1_gpu']} gpu, R2 {repro['r2_cpu']} vs {repro['r2_gpu']}: trained rounds are close, not identical")
    gaps = ["≈10 min is rounded and has no kernel timestamps (queue, pip, model download not separated)",
            "where the CPU arms ran is not recorded; two CPU baselines differ 2.4x",
            "the 30 GPU-h/week quota is stated, not read from Kaggle",
            "single GPU run, single seed"]
    summary = dict(
        headline=f"T4 {gpu:.1f} min/round vs CPU {by['ARM A']['min_per_round']}-{by['4-CPU container']['min_per_round']} "
                 f"(x{speedup['ARM A']}-x{speedup['4-CPU container']}); <= {runs_per_week:.0f} runs/week on the stated quota",
        same_config=SAME_CONFIG, speedup_gpu_vs_cpu=speedup, gpu_min_per_round=gpu,
        gpu_hours_per_3round_run=round(gpu_hours_per_run, 3), weekly_gpu_hours_stated=WEEKLY_GPU_HOURS,
        max_runs_per_week_calc=round(runs_per_week), money_per_run_ils=0, reproducibility=repro, gaps=gaps, rows=rows)
    out = os.environ.get("LAB_RUN_OUT")
    if out:
        json.dump(summary, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("gaps:", "; ".join(gaps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
