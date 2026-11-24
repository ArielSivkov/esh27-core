"""D1 (Kaggle T4): inside TripoSR. H1 layer-wise linear probe for log(floors) with permutation null + simple-feature control;
H2 causal vertical-stretch intervention on the mesh aspect. See PREREG_d1_inside.md."""
import io, json, time, subprocess, sys, os
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
def sh(c): r = subprocess.run(c, shell=True, capture_output=True, text=True); log("$", c[:70], "rc", r.returncode); return r.returncode
sh("git clone -q https://github.com/VAST-AI-Research/TripoSR /kaggle/working/TripoSR")
sh("pip install -q trimesh omegaconf einops rembg onnxruntime huggingface-hub 'transformers==4.46.3' scikit-learn")
os.makedirs("/kaggle/working/shim", exist_ok=True)
open("/kaggle/working/shim/torchmcubes.py", "w").write("""import torch, numpy as np
from skimage import measure
def marching_cubes(vol, thresh):
    v = vol.detach().float().cpu().numpy(); verts, faces, _, _ = measure.marching_cubes(v, level=thresh)
    return torch.from_numpy(verts.copy()).float().to(vol.device), torch.from_numpy(faces.astype(np.int64).copy()).to(vol.device)
""")
sys.path.insert(0, "/kaggle/working/shim"); sys.path.insert(0, "/kaggle/working/TripoSR")
import numpy as np, requests, torch
from PIL import Image
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground
import rembg
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import LeaveOneOut, cross_val_predict
BASE = "https://raw.githubusercontent.com/ArielSivkov/esh27-core/ccr-57cf16bc-k7n9ua/lab/interior/davinci/renders/"
meta = [m for m in requests.get(BASE + "meta.json", timeout=60).json() if m["fits"]]
log("images (fits)", len(meta))
model = TSR.from_pretrained("stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt"); model.renderer.set_chunk_size(8192); model.to("cuda").eval()
enc = model.image_tokenizer.model; layers = enc.encoder.layer; feats = {}
def mk(i):
    def hook(mod, inp, out): feats[i] = (out[0] if isinstance(out, tuple) else out).detach().float().mean(1).cpu().numpy()[0]
    return hook
for i, l in enumerate(layers): l.register_forward_hook(mk(i))
sess = rembg.new_session()
def prep(im, box, sy=1.0):
    x0, x1, yt, yb = box; mx, my = 0.1 * (x1 - x0), 0.1 * (yb - yt)
    crop = im.crop((max(0, int(x0 - mx)), max(0, int(yt - my)), min(im.width, int(x1 + mx)), min(im.height, int(yb + my))))
    if sy != 1.0: crop = crop.resize((crop.width, max(8, int(round(crop.height * sy)))), Image.BICUBIC)
    fg = resize_foreground(remove_background(crop, sess), 0.85)
    a = np.array(fg).astype(np.float32) / 255.0; a = a[:, :, :3] * a[:, :, 3:4] + (1 - a[:, :, 3:4]) * 0.5
    return Image.fromarray((a * 255).astype(np.uint8))
X = {i: [] for i in range(len(layers))}; y = []; simple = []; ims = {}
for m in meta:
    im = Image.open(io.BytesIO(requests.get(BASE + m["file"], timeout=60).content)).convert("RGB"); ims[m["file"]] = im
    with torch.no_grad(): model([prep(im, m["box"])], device="cuda")
    for i in X: X[i].append(feats[i])
    y.append(np.log(m["f"])); x0, x1, yt, yb = m["box"]; simple.append([np.log((yb - yt) / (x1 - x0)), np.log((yb - yt) * (x1 - x0))])
y = np.array(y); simple = np.array(simple); log("features done", len(y))
def loo_r2(Xm, yy):
    p = cross_val_predict(RidgeCV(alphas=[0.1, 1, 10, 100]), Xm, yy, cv=LeaveOneOut())
    return float(1 - ((yy - p) ** 2).sum() / ((yy - yy.mean()) ** 2).sum())
rng = np.random.default_rng(27); H1 = {"n": len(y), "layers": {}}
for i in X:
    Xm = np.array(X[i]); Xm = (Xm - Xm.mean(0)) / (Xm.std(0) + 1e-6)
    r2 = loo_r2(Xm, y); null = [loo_r2(Xm, rng.permutation(y)) for _ in range(200)]
    H1["layers"][i] = {"r2": round(r2, 3), "null95": round(float(np.percentile(null, 95)), 3)}
    log("layer", i, H1["layers"][i])
best = max(H1["layers"], key=lambda i: H1["layers"][i]["r2"]); H1["best_layer"] = best
H1["simple_features_r2"] = round(loo_r2((simple - simple.mean(0)) / simple.std(0), y), 3)
H1["supported"] = H1["layers"][best]["r2"] > 0.5 and H1["layers"][best]["r2"] > H1["layers"][best]["null95"]
print("=====H1=====\n" + json.dumps(H1, indent=1), flush=True)
# H2: vertical stretch intervention
sub = [m for m in meta if m["set"] == "C"]; rng2 = np.random.default_rng(29); sub = [sub[i] for i in rng2.choice(len(sub), min(15, len(sub)), replace=False)]
def aspect(img):
    with torch.no_grad(): codes = model([img], device="cuda"); mesh = model.extract_mesh(codes, True, resolution=192)[0]
    e = mesh.vertices.max(0) - mesh.vertices.min(0); return e
S = [0.8, 0.9, 1.0, 1.1, 1.25]; rows = []
for m in sub:
    exts = [aspect(prep(ims[m["file"]], m["box"], s)) for s in S]; rows.append({"file": m["file"], "f": m["f"], "ext": [e.tolist() for e in exts]})
    print("H2ROW " + json.dumps(rows[-1]), flush=True)
E = np.array([r["ext"] for r in rows])  # (n, 5, 3)
# vertical axis: v2 found axis 0 vertical, axis 2 horizontal (determined without truth); reuse
ratio = E[:, :, 0] / E[:, :, 2]; ls = np.log(S)
slopes = [float(np.polyfit(ls, np.log(r), 1)[0]) for r in ratio]
H2 = {"n": len(rows), "median_elasticity": round(float(np.median(slopes)), 3), "iqr": [round(float(np.percentile(slopes, 25)), 3), round(float(np.percentile(slopes, 75)), 3)],
      "per_building": [round(s, 3) for s in slopes]}
e = H2["median_elasticity"]; H2["outcome"] = "copies image proportions" if 0.5 <= e <= 1.5 else ("ignores them (own prior)" if e < 0.3 else "partial")
print("=====H2=====\n" + json.dumps(H2, indent=1)); log("DONE")
