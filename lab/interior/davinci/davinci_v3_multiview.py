"""Da Vinci v3 (Kaggle T4): COLMAP (pycolmap) vs VGGT-1B on Ariel's 14 Givat Yona photos. See PREREG_v3_multiview.md."""
import io, json, time, subprocess, sys, os, base64, shutil
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
def sh(c): r = subprocess.run(c, shell=True, capture_output=True, text=True); log("$", c[:70], "rc", r.returncode, (r.stderr or "")[-250:] if r.returncode else ""); return r.returncode
sh("pip install -q pycolmap")
sh("pip install -q git+https://github.com/facebookresearch/vggt")
import numpy as np, requests
from PIL import Image
RAW = "https://raw.githubusercontent.com/ArielSivkov/codesandbox-template-nuxt/twin-world/twin/data/photos/"
D = "/kaggle/working/imgs"; os.makedirs(D, exist_ok=True); names = []
for i in range(83, 97):
    n = f"{i:03d}.jpg"; r = requests.get(RAW + n, timeout=60)
    if r.ok:
        im = Image.open(io.BytesIO(r.content)).convert("RGB"); im.thumbnail((1600, 1600)); im.save(f"{D}/{n}", quality=92); names.append(n)
log("photos", len(names))
def rel_rot(Ra, Rb): return Rb @ Ra.T
def ang(R): return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
def emit_cloud(tag, xyz, rgb, n=20000):
    if len(xyz) == 0: return
    idx = np.random.default_rng(27).choice(len(xyz), min(n, len(xyz)), replace=False); xyz, rgb = xyz[idx], rgb[idx]
    c = xyz.mean(0); s = np.percentile(np.linalg.norm(xyz - c, axis=1), 95) or 1.0; q = np.clip((xyz - c) / s, -4, 4)
    arr = np.concatenate([(q * 8000).astype(np.int16).reshape(-1), np.zeros(0, np.int16)]).tobytes() + rgb.astype(np.uint8).reshape(-1).tobytes()
    print(f"CLOUD {json.dumps({'tag': tag, 'n': len(q)})} " + base64.b64encode(arr).decode(), flush=True)
S = {"photos": len(names)}; colmap_R = {}
try:
    import pycolmap
    db, out = "/kaggle/working/db.db", "/kaggle/working/sfm"; shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    pycolmap.extract_features(db, D); pycolmap.match_exhaustive(db)
    maps = pycolmap.incremental_mapping(db, D, out)
    if maps:
        best = max(maps.values(), key=lambda r: r.num_reg_images())
        S["colmap"] = {"models": len(maps), "registered": best.num_reg_images(), "points": best.num_points3D(),
                       "mean_reproj_px": round(best.compute_mean_reprojection_error(), 3),
                       "registered_names": sorted(im.name for im in best.images.values() if im.has_pose)}
        for im in best.images.values():
            if im.has_pose: colmap_R[im.name] = np.array(im.cam_from_world().rotation.matrix())
        P = np.array([p.xyz for p in best.points3D.values()]); C = np.array([p.color for p in best.points3D.values()])
        emit_cloud("colmap", P, C)
    else: S["colmap"] = {"models": 0, "registered": 0}
except Exception as e: S["colmap"] = {"error": repr(e)[:300]}
log("colmap", json.dumps(S.get("colmap"))[:300])
try:
    import torch
    from vggt.models.vggt import VGGT
    from vggt.utils.load_fn import load_and_preprocess_images
    from vggt.utils.pose_enc import pose_encoding_to_extri_intri
    model = VGGT.from_pretrained("facebook/VGGT-1B").to("cuda").eval()
    paths = [f"{D}/{n}" for n in names]; images = load_and_preprocess_images(paths).to("cuda")
    with torch.no_grad(), torch.cuda.amp.autocast(dtype=torch.float16):
        pred = model(images)
    extr, intr = pose_encoding_to_extri_intri(pred["pose_enc"], images.shape[-2:])
    E = extr[0].float().cpu().numpy(); vR = {n: E[i][:3, :3] for i, n in enumerate(names)}
    wp = pred["world_points"][0].float().cpu().numpy(); conf = pred["world_points_conf"][0].float().cpu().numpy()
    img = images.float().cpu().numpy().transpose(0, 2, 3, 1)
    m = conf > np.percentile(conf, 70); xyz = wp[m]; rgb = (img[m] * 255).clip(0, 255)
    S["vggt"] = {"points_kept": int(m.sum()), "conf_p70": float(np.percentile(conf, 70))}
    emit_cloud("vggt", xyz, rgb)
    common = [n for n in names if n in colmap_R]
    if len(common) >= 2:
        a = []
        for i in range(len(common)):
            for j in range(i + 1, len(common)):
                Rc = rel_rot(colmap_R[common[i]], colmap_R[common[j]]); Rv = rel_rot(vR[common[i]], vR[common[j]])
                a.append(ang(Rc @ Rv.T))
        S["crosscheck"] = {"pairs": len(a), "median_deg": round(float(np.median(a)), 2), "p90_deg": round(float(np.percentile(a, 90)), 2)}
    else: S["crosscheck"] = {"pairs": 0}
except Exception as e: S["vggt"] = {"error": repr(e)[:400]}
print("=====SUMMARY=====\n" + json.dumps(S, indent=1)); log("DONE")
