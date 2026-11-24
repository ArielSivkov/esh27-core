"""City v1 (Kaggle T4): Qwen2.5-VL-3B on the 53 Ashdod Commons street photos. See PREREG.md. Prints JSON lines to the log."""
import csv, io, json, re, sys, time, urllib.parse, subprocess
import requests, torch
from PIL import Image
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
CAT = "https://raw.githubusercontent.com/ArielSivkov/codesandbox-template-nuxt/twin-world/twin/publicdata/images_catalog.csv"
rows = list(csv.DictReader(io.StringIO(requests.get(CAT, timeout=60).text)))
log("catalog rows", len(rows))
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
MID = "Qwen/Qwen2.5-VL-3B-Instruct"
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(MID, torch_dtype=torch.float16, device_map="cuda:0")
proc = AutoProcessor.from_pretrained(MID, min_pixels=256 * 28 * 28, max_pixels=768 * 28 * 28)
P = {"a": 'Look at this street photo. Answer ONLY with JSON: {"floors": <integer number of above-ground floors of the most prominent building, or null if no building>, "text": [<every readable sign or street name, exactly as written>], "scene": "<one of: residential, commercial, tower, beach, park, road, other>"}',
     "b": 'You are surveying buildings. Count the storeys of the largest building visible in the image (ground floor counts as 1). Also transcribe any legible writing. Reply with JSON only: {"floors": int or null, "text": [strings], "scene": "residential|commercial|tower|beach|park|road|other"}'}
UA = {"User-Agent": "research-lab-image-analysis/0.1 (non-commercial)"}
def get_img(fname):
    u = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(fname) + "?width=1024"
    r = requests.get(u, headers=UA, timeout=60); r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")
@torch.no_grad()
def ask(img, prompt):
    msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inp = proc(text=[text], images=[img], return_tensors="pt").to("cuda:0")
    out = model.generate(**inp, max_new_tokens=160, do_sample=False)
    return proc.batch_decode(out[:, inp["input_ids"].shape[1]:], skip_special_tokens=True)[0]
def parse(s):
    m = re.search(r"\{.*\}", s, re.S)
    try: return json.loads(m.group(0)) if m else None
    except Exception: return None
res = []
for i, r in enumerate(rows):
    fn = r["file_name"]
    try: img = get_img(fn)
    except Exception as e: log("img fail", i, repr(e)[:100]); res.append({"i": i, "err": "download"}); continue
    out = {"i": i, "street": r.get("street", ""), "what": r.get("what_it_shows", "")[:80]}
    for k, pr in P.items():
        raw = ask(img, pr); js = parse(raw); out[k] = js if js is not None else {"raw": raw[:200]}
    res.append(out); print("ROW " + json.dumps(out, ensure_ascii=False), flush=True)
    time.sleep(0.5)
def norm(s): return re.sub(r"[\sויֿ\"'״׳\-]", "", (s or "").replace("רחוב", "").replace("רח'", ""))
fa = [(x["a"].get("floors"), x["b"].get("floors")) for x in res if "a" in x and isinstance(x["a"], dict) and isinstance(x["b"], dict)]
both = [(int(a), int(b)) for a, b in fa if isinstance(a, (int, float)) and isinstance(b, (int, float))]
agree = sum(abs(a - b) <= 1 for a, b in both)
street_hits, street_match = 0, 0
for x in res:
    if "a" not in x: continue
    texts = [t for k in ("a", "b") if isinstance(x[k], dict) for t in (x[k].get("text") or []) if isinstance(t, str)]
    st = norm(x["street"])
    if not st: continue
    heb = [t for t in texts if re.search(r"[֐-׿]", t)]
    if heb:
        street_hits += 1; street_match += any(st in norm(t) or (norm(t) and norm(t) in st and len(norm(t)) >= 3) for t in heb)
S = {"images": len(rows), "analysed": sum("a" in x for x in res), "floors_both_prompts": len(both),
     "floors_agree_within1": agree, "floors_agree_share": round(agree / len(both), 3) if both else None,
     "hebrew_text_read_on": street_hits, "of_which_matches_catalog_street": street_match,
     "coverage_floor_any": sum(1 for a, b in fa if isinstance(a, (int, float)) or isinstance(b, (int, float)))}
print("=====SUMMARY=====\n" + json.dumps(S, ensure_ascii=False, indent=1)); log("DONE")
