"""Da Vinci v1 (Kaggle T4): OWLv2 vs Grounding DINO window detection → rows → floors, on twin-world renders. See PREREG_v1_detect.md."""
import io, json, time, subprocess
import numpy as np, requests, torch
from PIL import Image
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
BASE = "https://raw.githubusercontent.com/ArielSivkov/esh27-core/ccr-57cf16bc-k7n9ua/lab/interior/davinci/renders/"
meta = requests.get(BASE + "meta.json", timeout=60).json()
imgs = {m["file"]: Image.open(io.BytesIO(requests.get(BASE + m["file"], timeout=60).content)).convert("RGB") for m in meta}
log("renders", len(imgs))
def rows_from_boxes(boxes, box):
    x0, x1, yt, yb = box
    c = [((b[1] + b[3]) / 2, b[3] - b[1]) for b in boxes if x0 <= (b[0] + b[2]) / 2 <= x1 and yt <= (b[1] + b[3]) / 2 <= yb]
    if not c: return 0, 0
    c.sort(); mh = float(np.median([h for _, h in c])); rows, cur, last = [], 1, c[0][0]
    for y, h in c[1:]:
        if y - last > 0.6 * mh: rows.append(cur); cur = 1
        else: cur += 1
        last = y
    rows.append(cur)
    return sum(r >= 2 for r in rows), len(c)
from transformers import Owlv2Processor, Owlv2ForObjectDetection, AutoProcessor, AutoModelForZeroShotObjectDetection
dev = "cuda"
res = {m["file"]: {"f": m["f"], "fits": m["fits"], "set": m["set"]} for m in meta}
try:
    p = Owlv2Processor.from_pretrained("google/owlv2-base-patch16-ensemble"); mdl = Owlv2ForObjectDetection.from_pretrained("google/owlv2-base-patch16-ensemble").to(dev).eval()
    for m in meta:
        im = imgs[m["file"]]; inp = p(text=[["a window"]], images=im, return_tensors="pt").to(dev)
        with torch.no_grad(): out = mdl(**inp)
        size = max(im.size); r = p.post_process_object_detection(out, threshold=0.15, target_sizes=torch.tensor([[size, size]]).to(dev))[0]
        boxes = r["boxes"].cpu().numpy().tolist(); fl, nb = rows_from_boxes(boxes, m["box"])
        res[m["file"]]["owl"] = fl; res[m["file"]]["owl_boxes"] = nb
    del mdl; torch.cuda.empty_cache(); log("owlv2 done")
except Exception as e: log("OWL FAILED", repr(e)[:300])
try:
    gp = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-base"); gm = AutoModelForZeroShotObjectDetection.from_pretrained("IDEA-Research/grounding-dino-base").to(dev).eval()
    for m in meta:
        im = imgs[m["file"]]; inp = gp(images=im, text="window.", return_tensors="pt").to(dev)
        with torch.no_grad(): out = gm(**inp)
        try: r = gp.post_process_grounded_object_detection(out, inp.input_ids, threshold=0.25, text_threshold=0.25, target_sizes=[im.size[::-1]])[0]
        except TypeError: r = gp.post_process_grounded_object_detection(out, inp.input_ids, box_threshold=0.25, text_threshold=0.25, target_sizes=[im.size[::-1]])[0]
        boxes = r["boxes"].cpu().numpy().tolist(); fl, nb = rows_from_boxes(boxes, m["box"])
        res[m["file"]]["gdino"] = fl; res[m["file"]]["gdino_boxes"] = nb
    log("gdino done")
except Exception as e: log("GDINO FAILED", repr(e)[:300])
for k, v in res.items(): print("ROW " + json.dumps({"file": k, **v}))
ev = [v for v in res.values() if v["fits"]]
S = {"n_fits": len(ev)}
for arm in ("owl", "gdino"):
    ok = [v for v in ev if arm in v]
    S[arm] = {"within1": sum(abs(v[arm] - v["f"]) <= 1 for v in ok), "n": len(ok),
              "towers_within1": sum(abs(v[arm] - v["f"]) <= 1 for v in ok if v["f"] >= 20), "towers_n": sum(v["f"] >= 20 for v in ok)}
S["baseline4"] = {"within1": sum(abs(4 - v["f"]) <= 1 for v in ev), "n": len(ev)}
print("=====SUMMARY=====\n" + json.dumps(S, indent=1)); log("DONE")
