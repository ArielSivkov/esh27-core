"""Da Vinci v0: building geometry from an image without counting.
Floor pitch = dominant period of horizontal edges (autocorrelation) inside the building box; floors = box height / pitch.
Also: bay pitch (horizontal period) and a 4-color palette. numpy + PIL only.
Usage: python davinci_v0.py meta.json out.json"""
import json, sys
import numpy as np
from PIL import Image

def period(profile, lo, hi):
    x = profile - np.convolve(profile, np.ones(15) / 15, mode="same")  # remove slow trend
    x = x - x.mean()
    if not np.any(x): return None, 0.0
    ac = np.correlate(x, x, mode="full")[len(x) - 1:]; ac = ac / ac[0]
    hi = min(hi, len(ac) - 2)
    if hi <= lo: return None, 0.0
    seg = ac[lo:hi + 1]
    peaks = [i for i in range(1, len(seg) - 1) if seg[i] > seg[i - 1] and seg[i] >= seg[i + 1] and seg[i] > 0.15]
    if not peaks: return None, 0.0
    best = max(peaks, key=lambda i: seg[i])
    # prefer the smallest lag whose peak is ≥ 80% of the best (avoid picking 2× the period)
    first = min(i for i in peaks if seg[i] >= 0.8 * seg[best])
    return lo + first, float(seg[first])

def palette(rgb, k=4, iters=12, seed=27):
    px = rgb.reshape(-1, 3).astype(float)
    rng = np.random.default_rng(seed); px = px[rng.choice(len(px), min(4000, len(px)), replace=False)]
    c = px[rng.choice(len(px), k, replace=False)]
    for _ in range(iters):
        lab = ((px[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        c = np.array([px[lab == j].mean(0) if np.any(lab == j) else c[j] for j in range(k)])
    share = np.bincount(lab, minlength=k) / len(lab)
    o = np.argsort(-share)
    return [{"hex": "#%02x%02x%02x" % tuple(int(v) for v in c[j]), "share": round(float(share[j]), 3)} for j in o]

def analyse(img_path, box):
    im = Image.open(img_path).convert("RGB"); W, H = im.size
    x0, x1, yt, yb = box
    clipped = yt < 0 or yb > H or x0 < 0 or x1 > W
    xa, xb = int(max(0, x0)), int(min(W, x1)); ya, yb2 = int(max(0, yt)), int(min(H, yb))
    if xb - xa < 20 or yb2 - ya < 30: return {"status": "too small"}
    rgb = np.asarray(im)[ya:yb2, xa:xb].astype(float); g = rgb.mean(2)
    cx0, cx1 = int(0.25 * g.shape[1]), int(0.75 * g.shape[1])  # central half: least occlusion/edge effects
    gy = np.abs(np.diff(g[:, cx0:cx1], axis=0)).mean(1)
    gx = np.abs(np.diff(g, axis=1)).mean(0)
    span = yb2 - ya
    pf, sf = period(gy, 6, int(span / 1.5))
    pb, sb = period(gx, 6, int((xb - xa) / 1.5))
    out = {"status": "ok", "clipped": bool(clipped), "box_h_px": round(yb - yt, 1), "floor_pitch_px": pf, "floor_conf": round(sf, 3),
           "bay_pitch_px": pb, "bay_conf": round(sb, 3), "palette": palette(rgb)}
    out["floors_est"] = round((yb - yt) / pf, 2) if pf else None
    return out

if __name__ == "__main__":
    meta = json.load(open(sys.argv[1])); res = []
    for m in meta:
        r = analyse(m["file"], (m["x0"], m["x1"], m["ytop"], m["ybase"]))
        res.append({"id": m["id"], "f_true": m["f"], "d": round(m["d"], 1), **r})
    json.dump(res, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
    ok = [r for r in res if r.get("floors_est") is not None and not r["clipped"]]
    for r in res: print(r["f_true"], r["id"], r.get("status"), "clipped" if r.get("clipped") else "", "est", r.get("floors_est"), "pitch", r.get("floor_pitch_px"), "conf", r.get("floor_conf"))
    def score(rs, pred):
        return sum(abs(pred(r) - r["f_true"]) <= 1 for r in rs), len(rs)
    for name, rs in [("all unclipped", ok), ("low f<=8", [r for r in ok if r["f_true"] <= 8]), ("towers f>=20", [r for r in ok if r["f_true"] >= 20])]:
        dv, n = score(rs, lambda r: r["floors_est"]); bl, _ = score(rs, lambda r: 4)
        print(f"{name}: davinci within±1 {dv}/{n}  | baseline(4) {bl}/{n}")
    print("excluded (clipped or no period):", len(res) - len(ok))
