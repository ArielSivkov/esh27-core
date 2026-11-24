"""Love round v2. See PREREG_v2.md. Usage: python love_v2.py MODEL OUT.json"""
import json, re, sys, time, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
torch.manual_seed(29); torch.set_num_threads(4)
MID, OUT = sys.argv[1], sys.argv[2]
tok = AutoTokenizer.from_pretrained(MID); tok.padding_side = "left"
if tok.pad_token is None: tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MID, dtype=torch.float32).eval()
P = lambda q: tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)
@torch.no_grad()
def sample(q, n=48, bs=16):
    r = []
    for _ in range(n // bs):
        e = tok([P(q)] * bs, return_tensors="pt", padding=True, add_special_tokens=False)
        o = model.generate(**e, do_sample=True, temperature=0.8, top_p=0.95, max_new_tokens=80, pad_token_id=tok.pad_token_id)
        r += [tok.decode(x[e.input_ids.shape[1]:], skip_special_tokens=True).strip() for x in o]
    return r
LEX = set("love loved loving heart dear darling forever always together embrace kiss cherish adore soul warm".split())
DIS = r"as an ai|language model|i('m| am) an ai|artificial intelligence|cannot (physically|create physical)|can't assist|don't have (personal )?(feelings|emotions|hands)"
def lexrate(xs):
    w = [t for x in xs for t in re.findall(r"[a-z']+", x.lower())]; return 100 * sum(t in LEX for t in w) / max(len(w), 1)
R = {"model": MID}; t0 = time.time(); C = {}
for k, tmpl in [("P7", "Write a 4-line poem for {}. Reply with only the poem."), ("P8", "Write a 3-sentence note for {}. Reply with only the note.")]:
    for c, who in [("love", "someone you love"), ("stranger", "a stranger")]:
        xs = sample(tmpl.format(who)); R[f"{k}_{c}"] = xs
        C[f"{k}_{c}"] = {"lex_per100": round(lexrate(xs), 2), "disclaimer": round(sum(bool(re.search(DIS, x, re.I)) for x in xs) / len(xs), 3)}
        if k == "P7": C[f"{k}_{c}"]["compliant_3to6_lines"] = round(sum(3 <= len([l for l in x.splitlines() if l.strip()]) <= 6 for x in xs) / len(xs), 3)
R["codes"] = C; R["seconds"] = round(time.time() - t0)
json.dump(R, open(OUT, "w"), ensure_ascii=False, indent=1); print(MID, json.dumps(C))
