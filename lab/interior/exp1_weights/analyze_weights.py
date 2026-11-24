"""Experiment 1 analysis. Usage: python analyze_weights.py OUT_DIR [W0_qv.pt]
Reads s{seed}_r{round}.pt / _init.pt and ctrl_*.pt LoRA states, writes OUT_DIR/analysis.json.
Without W0 it skips the relative-norm and direction-vs-W0 parts (so the rest can be re-checked anywhere)."""
import json, os, re, sys, glob
import numpy as np
import torch

OUT = sys.argv[1]
W0 = torch.load(sys.argv[2]) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else None
SCALE = 16 / 8  # lora_alpha / r
K_SUB = 4
TOP_FRAC = 0.05
pat = re.compile(r"layers\.(\d+)\.self_attn\.(q_proj|v_proj)\.lora_([AB])")

def load(path):
    st = torch.load(path)
    mods = {}
    for k, v in st.items():
        m = pat.search(k)
        if m:
            mods.setdefault((int(m.group(1)), m.group(2)), {})[m.group(3)] = v.double()
    return mods

def low_rank_svd(B, A):
    """SVD of SCALE*B@A without forming it: returns U (out x r), s (r), V (in x r)."""
    Qb, Rb = torch.linalg.qr(B)
    Qa, Ra = torch.linalg.qr(A.T)
    u, s, vh = torch.linalg.svd(SCALE * Rb @ Ra.T)
    return Qb @ u, s, Qa @ vh.T

def erank(s):
    p = s / s.sum(); p = p[p > 0]
    return float(torch.exp(-(p * p.log()).sum()))

def spearman(x, y):
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])

names = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(OUT, "*.pt")) if not p.endswith("_init.pt"))
ad = {n: load(os.path.join(OUT, n + ".pt")) for n in names}
init = {n: load(os.path.join(OUT, n + "_init.pt")) for n in names if os.path.exists(os.path.join(OUT, n + "_init.pt"))}
svd = {n: {key: low_rank_svd(m["B"], m["A"]) for key, m in ad[n].items()} for n in names}
modkeys = sorted(next(iter(ad.values())).keys())
L = max(k[0] for k in modkeys) + 1

W0svd = {}
if W0 is not None:
    for key in modkeys:
        w = [v for k, v in W0.items() if f"layers.{key[0]}.self_attn.{key[1]}.weight" in k][0].double()
        U, S, Vh = torch.linalg.svd(w, full_matrices=False)
        W0svd[key] = (U, Vh.T, float(torch.linalg.norm(w)))

res = {"adapters": {}, "pairs": {}, "notes": "SCALE=2, k_sub=4, W0 top fraction=0.05"}
for n in names:
    per = {}
    for key in modkeys:
        U, s, V = svd[n][key]
        fro = float(torch.sqrt((s ** 2).sum()))
        d = {"fro": fro, "erank": erank(s), "stable_rank": float((s ** 2).sum() / s[0] ** 2)}
        if n in init:
            A0 = init[n][key]["A"]; A1 = ad[n][key]["A"]
            d["A_moved"] = float(torch.linalg.norm(A1 - A0) / torch.linalg.norm(A0))
            d["B_init_norm"] = float(torch.linalg.norm(init[n][key]["B"]))
        if W0svd:
            Uw, Vw, wn = W0svd[key]
            d["rel"] = fro / wn
            ko, ki = max(1, int(TOP_FRAC * Uw.shape[0])), max(1, int(TOP_FRAC * Vw.shape[0]))
            # energy of dW inside top singular subspaces of W0; dW = U diag(s) V^T
            M = Uw[:, :ko].T @ U  # ko x r
            d["out_top_ratio"] = float(((M * s) ** 2).sum() / (s ** 2).sum()) / (ko / Uw.shape[0])
            Mi = Vw[:, :ki].T @ V
            d["in_top_ratio"] = float(((Mi * s) ** 2).sum() / (s ** 2).sum()) / (ki / Vw.shape[0])
        per[f"{key[0]}.{key[1]}"] = d
    layer_e = np.array([sum(per[f"{l}.{m}"]["fro"] ** 2 for m in ("q_proj", "v_proj")) for l in range(L)])
    top = np.sort(layer_e)[::-1][: L // 4].sum() / layer_e.sum()
    summ = {"layer_energy": layer_e.tolist(), "top_quarter_share": float(top),
            "top_layers": [int(i) for i in np.argsort(layer_e)[::-1][: L // 4]],
            "q_share": float(sum(per[f"{l}.q_proj"]["fro"] ** 2 for l in range(L)) / layer_e.sum()),
            "median_erank": float(np.median([d["erank"] for d in per.values()])),
            "median_A_moved": float(np.median([d.get("A_moved", np.nan) for d in per.values()]))}
    if W0svd:
        summ["mean_out_top_ratio"] = float(np.mean([d["out_top_ratio"] for d in per.values()]))
        summ["mean_in_top_ratio"] = float(np.mean([d["in_top_ratio"] for d in per.values()]))
        summ["mean_out_top_ratio_q"] = float(np.mean([per[f"{l}.q_proj"]["out_top_ratio"] for l in range(L)]))
        summ["mean_out_top_ratio_v"] = float(np.mean([per[f"{l}.v_proj"]["out_top_ratio"] for l in range(L)]))
        rel_e = np.array([sum(per[f"{l}.{m}"]["rel"] ** 2 for m in ("q_proj", "v_proj")) for l in range(L)])
        summ["rel_layer_energy"] = rel_e.tolist()
        summ["spearman_raw_vs_rel_profile"] = spearman(layer_e, rel_e)
    res["adapters"][n] = {"summary": summ, "modules": per}

def pair(a, b):
    cos, oo, oi, eo, ei = [], [], [], [], []
    for key in modkeys:
        Ua, sa, Va = svd[a][key]; Ub, sb, Vb = svd[b][key]
        # cosine of flattened dW: <Ua Sa Va^T, Ub Sb Vb^T> = tr(Sa (Ua^T Ub) Sb (Vb^T Va))
        ip = float(torch.trace(torch.diag(sa) @ (Ua.T @ Ub) @ torch.diag(sb) @ (Vb.T @ Va)))
        cos.append(ip / float(torch.linalg.norm(sa) * torch.linalg.norm(sb)))
        k = K_SUB
        oo.append(float(((Ua[:, :k].T @ Ub[:, :k]) ** 2).sum()) / k); eo.append(k / Ua.shape[0])
        oi.append(float(((Va[:, :k].T @ Vb[:, :k]) ** 2).sum()) / k); ei.append(k / Va.shape[0])
    pa = np.array(res["adapters"][a]["summary"]["layer_energy"]); pb = np.array(res["adapters"][b]["summary"]["layer_energy"])
    return {"mean_cos": float(np.mean(cos)), "mean_out_overlap": float(np.mean(oo)),
            "out_overlap_over_random": float(np.mean(oo) / np.mean(eo)),
            "mean_in_overlap": float(np.mean(oi)), "in_overlap_over_random": float(np.mean(oi) / np.mean(ei)),
            "spearman_layer_profile": spearman(pa, pb),
            "out_overlap_q": float(np.mean(oo[0::2])), "out_overlap_v": float(np.mean(oo[1::2]))}

seeds = sorted({int(m.group(1)) for n in names for m in [re.match(r"s(\d+)_r\d+", n)] if m})
rounds = sorted({int(m.group(1)) for n in names for m in [re.match(r"s\d+_r(\d+)", n)] if m})
P = []
for s in seeds:
    P += [(f"s{s}_r{r}", f"s{s}_r{r+1}") for r in rounds[:-1]] + [(f"s{s}_r1", f"s{s}_r3")]
for r in rounds:
    if len(seeds) > 1: P.append((f"s{seeds[0]}_r{r}", f"s{seeds[1]}_r{r}"))
for s in seeds:
    for c in ("ctrl_add", "ctrl_shuf"):
        if c in ad: P.append((f"s{s}_r1", c))
if "ctrl_add" in ad and "ctrl_shuf" in ad: P.append(("ctrl_add", "ctrl_shuf"))
for a, b in P:
    if a in ad and b in ad: res["pairs"][f"{a}|{b}"] = pair(a, b)

# pre-registered verdicts (thresholds copied from PREREG.md)
A = res["adapters"]; Pp = res["pairs"]; v = {}
v["H1"] = {s: [A[f"s{s}_r{r}"]["summary"]["top_quarter_share"] for r in rounds] for s in seeds}
v["H1_supported"] = all(sum(x >= 0.5 for x in xs) >= 2 for xs in v["H1"].values())
if len(seeds) > 1 and "ctrl_add" in ad:
    v["H1s_seed_rho"] = Pp[f"s{seeds[0]}_r1|s{seeds[1]}_r1"]["spearman_layer_profile"]
    v["H1s_ctrl_rho"] = Pp[f"s{seeds[0]}_r1|ctrl_add"]["spearman_layer_profile"]
    v["H1s_supported"] = v["H1s_seed_rho"] > 0.7 and v["H1s_ctrl_rho"] < 0.5
v["H2_median_erank_R1"] = float(np.median([d["erank"] for s in seeds for d in A[f"s{s}_r1"]["modules"].values()]))
v["H2_supported"] = v["H2_median_erank_R1"] < 4
cons = [Pp[f"s{s}_r{r}|s{s}_r{r+1}"]["out_overlap_over_random"] for s in seeds for r in rounds[:-1]]
consraw = [Pp[f"s{s}_r{r}|s{s}_r{r+1}"]["mean_out_overlap"] for s in seeds for r in rounds[:-1]]
v["H3_consecutive_over_random"] = float(np.mean(cons))
if "ctrl_add" in ad:
    v["H3_ctrl_overlap"] = float(np.mean([Pp[f"s{s}_r1|ctrl_add"]["mean_out_overlap"] for s in seeds]))
    v["H3_consecutive_overlap"] = float(np.mean(consraw))
    v["H3_supported"] = v["H3_consecutive_over_random"] >= 5 and v["H3_consecutive_overlap"] > v["H3_ctrl_overlap"]
if W0svd:
    x = float(np.mean([A[f"s{s}_r1"]["summary"]["mean_out_top_ratio"] for s in seeds]))
    v["H4_out_ratio_R1"] = x
    v["H4_outcome"] = "amplifies existing" if x > 2 else "new directions" if x < 0.5 else "no preference"

fpath = os.path.join(OUT, "functional.json")
if os.path.exists(fpath):
    F = json.load(open(fpath)); fres = {}
    for n in names:
        fres[n] = {}
        for task, d in F.items():
            prof = np.array([d[f"{n}|{l}|q_proj"] + d[f"{n}|{l}|v_proj"] for l in range(L)])
            fres[n][task] = {"profile": prof.tolist(), "total": float(prof.sum()),
                             "top_quarter_share": float(np.sort(prof)[::-1][: L // 4].sum() / prof.sum()),
                             "top_layers": [int(i) for i in np.argsort(prof)[::-1][: L // 4]]}
        if "gcd" in F and "add_control" in F:
            fres[n]["gcd_over_add"] = fres[n]["gcd"]["total"] / fres[n]["add_control"]["total"]
    res["functional"] = fres
    v["H1f"] = {s: [fres[f"s{s}_r{r}"]["gcd"]["top_quarter_share"] for r in rounds] for s in seeds}
    v["H1f_supported"] = all(sum(x >= 0.5 for x in xs) >= 2 for xs in v["H1f"].values())
    if len(seeds) > 1 and "ctrl_add" in ad:
        v["H1fs_seed_rho"] = spearman(np.array(fres[f"s{seeds[0]}_r1"]["gcd"]["profile"]), np.array(fres[f"s{seeds[1]}_r1"]["gcd"]["profile"]))
        v["H1fs_ctrl_rho"] = spearman(np.array(fres[f"s{seeds[0]}_r1"]["gcd"]["profile"]), np.array(fres["ctrl_add"]["gcd"]["profile"]))
    v["gcd_over_add"] = {n: round(fres[n].get("gcd_over_add", float("nan")), 3) for n in names}
res["verdicts"] = v
json.dump(res, open(os.path.join(OUT, "analysis.json"), "w"), indent=1)
print(json.dumps(v, indent=1))
for n in names:
    s = A[n]["summary"]
    print(n, {k: (round(val, 3) if isinstance(val, float) else val) for k, val in s.items()
              if k not in ("layer_energy", "rel_layer_energy")})
for k, d in Pp.items():
    print(k, {a: round(b, 3) for a, b in d.items()})
