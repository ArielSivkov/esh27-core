"""Da Vinci v2 (Kaggle T4): TripoSR image→mesh on twin-world renders → height via proportions × map width. See PREREG_v2_3d.md."""
import io, json, time, subprocess, sys, os, base64
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
def sh(c): r = subprocess.run(c, shell=True, capture_output=True, text=True); log("$", c[:80], "rc", r.returncode, (r.stderr or "")[-300:] if r.returncode else ""); return r.returncode
sh("git clone -q https://github.com/VAST-AI-Research/TripoSR /kaggle/working/TripoSR")
sh("pip install -q trimesh omegaconf einops rembg onnxruntime huggingface-hub 'transformers==4.46.3'")
rc = sh("pip install -q git+https://github.com/tatsy/torchmcubes.git")
if rc:  # fallback (A2, before results): a torchmcubes shim on scikit-image's marching cubes
    os.makedirs("/kaggle/working/shim", exist_ok=True)
    open("/kaggle/working/shim/torchmcubes.py", "w").write("""import torch, numpy as np
from skimage import measure
def marching_cubes(vol, thresh):
    v = vol.detach().float().cpu().numpy()
    verts, faces, _, _ = measure.marching_cubes(v, level=thresh)
    return torch.from_numpy(verts.copy()).float().to(vol.device), torch.from_numpy(faces.astype(np.int64).copy()).to(vol.device)
""")
    sys.path.insert(0, "/kaggle/working/shim"); log("using torchmcubes shim (skimage)")
sys.path.insert(0, "/kaggle/working/TripoSR")
import numpy as np, requests, torch, trimesh
from PIL import Image
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground
import rembg
BASE = "https://raw.githubusercontent.com/ArielSivkov/esh27-core/ccr-57cf16bc-k7n9ua/lab/interior/davinci/renders/"
meta = [m for m in requests.get(BASE + "meta.json", timeout=60).json() if m["fits"]]
model = TSR.from_pretrained("stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt"); model.renderer.set_chunk_size(8192); model.to("cuda")
sess = rembg.new_session(); rows = []; demo_ids = {}
for m in meta:
    im = Image.open(io.BytesIO(requests.get(BASE + m["file"], timeout=60).content)).convert("RGB")
    x0, x1, yt, yb = m["box"]; mx, my = 0.1 * (x1 - x0), 0.1 * (yb - yt)
    crop = im.crop((max(0, int(x0 - mx)), max(0, int(yt - my)), min(im.width, int(x1 + mx)), min(im.height, int(yb + my))))
    fg = resize_foreground(remove_background(crop, sess), 0.85)
    a = np.array(fg).astype(np.float32) / 255.0; a = a[:, :, :3] * a[:, :, 3:4] + (1 - a[:, :, 3:4]) * 0.5
    img = Image.fromarray((a * 255).astype(np.uint8))
    with torch.no_grad():
        codes = model([img], device="cuda"); mesh = model.extract_mesh(codes, True, resolution=256)[0]
    ext = (mesh.vertices.max(0) - mesh.vertices.min(0)).tolist()
    r = {"file": m["file"], "f": m["f"], "h_true": m["h_true"], "w_perp_m": m["w_perp_m"], "box_h_px": yb - yt, "box_w_px": x1 - x0, "ext": ext, "faces": len(mesh.faces)}
    rows.append(r); print("ROW " + json.dumps(r), flush=True)
    if m["f"] in (2, 4, 30) and m["f"] not in demo_ids:
        demo_ids[m["f"]] = m["file"]; s = mesh.simplify_quadric_decimation(face_count=3000) if hasattr(mesh, "simplify_quadric_decimation") else mesh
        buf = io.StringIO(); s.export(buf, file_type="obj") if False else None
        obj = trimesh.exchange.obj.export_obj(s, include_color=False, include_texture=False, include_normals=False)
        print("OBJ " + json.dumps({"f": m["f"], "file": m["file"]}) + " " + base64.b64encode(obj.encode()).decode(), flush=True)
E = np.array([r["ext"] for r in rows]); bh = np.array([r["box_h_px"] for r in rows]); bw = np.array([r["box_w_px"] for r in rows])
cor = lambda a, b: float(np.corrcoef(a, b)[0, 1])
vi = int(np.argmax([cor(E[:, i], bh) for i in range(3)])); hi = int(np.argmax([cor(E[:, i], bw) if i != vi else -9 for i in range(3)]))
h_true = np.array([r["h_true"] for r in rows]); W = np.array([r["w_perp_m"] for r in rows])
H3d = E[:, vi] / E[:, hi] * W; Hbox = bh / bw * W
tol = np.maximum(3.0, 0.2 * h_true)
S = {"n": len(rows), "vertical_axis": vi, "horizontal_axis": hi, "axis_corrs_h": [round(cor(E[:, i], bh), 3) for i in range(3)],
     "tripo_within_tol": int((np.abs(H3d - h_true) <= tol).sum()), "box_ratio_within_tol": int((np.abs(Hbox - h_true) <= tol).sum()),
     "baseline13_within_tol": int((np.abs(13 - h_true) <= tol).sum()),
     "tripo_median_abs_err_m": round(float(np.median(np.abs(H3d - h_true))), 2), "box_median_abs_err_m": round(float(np.median(np.abs(Hbox - h_true))), 2),
     "per_image": [[r["file"], r["h_true"], round(float(a), 1), round(float(b), 1)] for r, a, b in zip(rows, H3d, Hbox)]}
print("=====SUMMARY=====\n" + json.dumps(S, indent=1)); log("DONE")
