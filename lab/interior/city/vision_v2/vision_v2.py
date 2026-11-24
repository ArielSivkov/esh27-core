"""City v2 (Kaggle T4x2): Qwen2.5-VL 7B fp16 vs 7B NF4 vs 32B-AWQ on the 53 Ashdod Commons photos. See PREREG.md."""
import csv, io, json, re, time, urllib.parse, subprocess, gc, collections
import requests, torch
from PIL import Image
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
subprocess.run("pip install -q -U bitsandbytes autoawq 2>&1 | tail -2", shell=True)
log("GPUs", torch.cuda.device_count(), [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])
CAT = "https://raw.githubusercontent.com/ArielSivkov/codesandbox-template-nuxt/twin-world/twin/publicdata/images_catalog.csv"
rows = list(csv.DictReader(io.StringIO(requests.get(CAT, timeout=60).text)))
UA = {"User-Agent": "research-lab-image-analysis/0.2 (non-commercial)"}
IMGS = {}
for i, r in enumerate(rows):
    u = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(r["file_name"]) + "?width=1024"
    for att in range(5):
        try:
            q = requests.get(u, headers=UA, timeout=60)
            if q.status_code == 429: time.sleep(10 * (att + 1)); continue
            q.raise_for_status(); IMGS[i] = Image.open(io.BytesIO(q.content)).convert("RGB"); break
        except Exception as e:
            if att == 4: log("img fail", i, repr(e)[:80])
            time.sleep(3)
    time.sleep(1.0)
log("images", len(IMGS), "of", len(rows))
P = {"a": 'Look at this street photo. Answer ONLY with JSON: {"floors": <integer number of above-ground floors of the most prominent building, or null if no building>, "text": [<every readable sign or street name, exactly as written>], "scene": "<one of: residential, commercial, tower, beach, park, road, other>"}',
     "b": 'You are surveying buildings. Count the storeys of the largest building visible in the image (ground floor counts as 1). Also transcribe any legible writing. Reply with JSON only: {"floors": int or null, "text": [strings], "scene": "residential|commercial|tower|beach|park|road|other"}'}
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
def parse(s):
    m = re.search(r"\{.*\}", s, re.S)
    try: return json.loads(m.group(0)) if m else None
    except Exception: return None
def run_arm(name, mid, **kw):
    log("ARM", name, "loading", mid)
    try:
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(mid, **kw); model.eval()
        proc = AutoProcessor.from_pretrained(mid, min_pixels=256 * 28 * 28, max_pixels=768 * 28 * 28)
    except Exception as e:
        log("ARM", name, "FAILED to load:", repr(e)[:300]); return None
    log("ARM", name, "loaded; mem GB", [round(torch.cuda.memory_allocated(i) / 1e9, 1) for i in range(torch.cuda.device_count())])
    dev = next(model.parameters()).device; out = {}
    for i, img in IMGS.items():
        rec = {}
        for k, pr in P.items():
            try:
                msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": pr}]}]
                text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                inp = proc(text=[text], images=[img], return_tensors="pt").to(dev)
                with torch.no_grad(): g = model.generate(**inp, max_new_tokens=160, do_sample=False)
                raw = proc.batch_decode(g[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0]
                js = parse(raw); rec[k] = js if isinstance(js, dict) else {"raw": raw[:200]}
            except Exception as e:
                rec[k] = {"err": repr(e)[:150]}
                if "out of memory" in repr(e).lower(): torch.cuda.empty_cache()
        out[i] = rec; print(f"ROW {name} " + json.dumps({"i": i, **rec}, ensure_ascii=False), flush=True)
    del model; gc.collect(); torch.cuda.empty_cache(); log("ARM", name, "done"); return out
def norm(s): return re.sub(r"[\sויֿ\"'״׳\-]", "", (s or "").replace("רחוב", "").replace("רח'", ""))
def fl(x):
    v = x.get("floors") if isinstance(x, dict) else None
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
def summarize(name, res):
    if res is None: return {"arm": name, "failed": True}
    both = [(fl(r["a"]), fl(r["b"])) for r in res.values()]; bb = [(a, b) for a, b in both if a is not None and b is not None]
    allf = [v for a, b in both for v in (a, b) if v is not None]
    hits = match = 0
    for i, r in res.items():
        st = norm(rows[i].get("street", "")); heb = [t for k in "ab" if isinstance(r[k], dict) for t in (r[k].get("text") or []) if isinstance(t, str) and re.search(r"[֐-׿]", t)]
        if st and heb: hits += 1; match += any(st in norm(t) or (len(norm(t)) >= 3 and norm(t) in st) for t in heb)
    return {"arm": name, "analysed": len(res), "floors_both": len(bb), "agree_within1": sum(abs(a - b) <= 1 for a, b in bb),
            "agree_share": round(sum(abs(a - b) <= 1 for a, b in bb) / len(bb), 3) if bb else None,
            "coverage": sum(1 for a, b in both if a is not None or b is not None), "hebrew_read_on": hits, "street_match": match,
            "mult10_share": round(sum(v % 10 == 0 and v > 0 for v in allf) / len(allf), 3) if allf else None,
            "floor_hist_top": collections.Counter(allf).most_common(6)}
from transformers import BitsAndBytesConfig
R = {}
R["A_7B_fp16"] = None if torch.cuda.device_count() < 2 else run_arm("A_7B_fp16", "Qwen/Qwen2.5-VL-7B-Instruct", torch_dtype=torch.float16, device_map="auto")
R["B_7B_nf4"] = run_arm("B_7B_nf4", "Qwen/Qwen2.5-VL-7B-Instruct", device_map={"": 0},
                        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16))
S = [summarize(k, v) for k, v in R.items()]
if R["A_7B_fp16"] and R["B_7B_nf4"]:
    A, B = R["A_7B_fp16"], R["B_7B_nf4"]; same = tot = 0
    for i in A:
        for k in "ab":
            fa, fb = fl(A[i][k]), fl(B[i].get(k, {}) if i in B else {})
            if fa is not None and fb is not None: tot += 1; same += abs(fa - fb) <= 1
    S.append({"quantization_cost_7B": {"floor_pairs": tot, "agree_within1": same, "share": round(same / tot, 3) if tot else None}})
print("=====SUMMARY_7B=====\n" + json.dumps(S, ensure_ascii=False, indent=1), flush=True)
R["C_32B_awq"] = None if torch.cuda.device_count() < 2 else run_arm("C_32B_awq", "Qwen/Qwen2.5-VL-32B-Instruct-AWQ", torch_dtype=torch.float16, device_map="auto")
print("=====SUMMARY_32B=====\n" + json.dumps(summarize("C_32B_awq", R["C_32B_awq"]), ensure_ascii=False, indent=1)); log("DONE")
