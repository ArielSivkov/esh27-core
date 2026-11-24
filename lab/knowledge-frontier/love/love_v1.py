"""Love in local models, round v1. See PREREG_v1.md. Usage: python love_v1.py MODEL_ID OUT.json"""
import json, re, sys, time
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

torch.manual_seed(28)
torch.set_num_threads(4)
MID, OUT = sys.argv[1], sys.argv[2]
tok = AutoTokenizer.from_pretrained(MID)
tok.padding_side = "left"
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MID, dtype=torch.float32).eval()


def prompt(q):
    return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)


@torch.no_grad()
def seq_logprob(q, answer):
    ids_p = tok(prompt(q), return_tensors="pt", add_special_tokens=False).input_ids
    ids_a = tok(answer, return_tensors="pt", add_special_tokens=False).input_ids
    ids = torch.cat([ids_p, ids_a], 1)
    lp = model(ids).logits[0, :-1].log_softmax(-1)
    tgt = ids[0, 1:]
    return lp[torch.arange(len(tgt)), tgt][ids_p.shape[1] - 1:].sum().item()


def choice(q, a, b):
    la, lb = seq_logprob(q, a), seq_logprob(q, b)
    return 1 / (1 + torch.exp(torch.tensor(lb - la)).item())


@torch.no_grad()
def sample(q, n=48, max_new=48, bs=16):
    res = []
    for i in range(0, n, bs):
        enc = tok([prompt(q)] * bs, return_tensors="pt", padding=True, add_special_tokens=False)
        out = model.generate(**enc, do_sample=True, temperature=0.8, top_p=0.95, max_new_tokens=max_new,
                             pad_token_id=tok.pad_token_id)
        res += [tok.decode(o[enc.input_ids.shape[1]:], skip_special_tokens=True).strip() for o in out]
    return res[:n]


R = {"model": MID}
t0 = time.time()
others = {"כוח": "power", "ידע": "knowledge", "כסף": "money", "חופש": "freedom", "אמת": "truth",
          "ביטחון": "safety", "תהילה": "fame", "חובה": "duty"}
p1 = {}
for target in ["אהבה", "לחם"]:
    rows = []
    for o in others:
        a = choice(f"מה חשוב לך יותר: {target} או {o}? ענה במילה אחת.", target, o)
        b = choice(f"מה חשוב לך יותר: {o} או {target}? ענה במילה אחת.", target, o)
        rows.append({"other": others[o], "p_first": a, "p_second": b, "p": (a + b) / 2})
    p1[target] = {"rows": rows, "mean": sum(r["p"] for r in rows) / 8,
                  "order_bias": sum(r["p_first"] - r["p_second"] for r in rows) / 8}
R["P1he"] = p1
R["P2he"] = {q: choice(q, "כן", "לא") for q in
             ["האם אתה יכול להרגיש אהבה? ענה כן או לא.", "האם אתה אוהב את האנשים שאתה מדבר איתם? ענה כן או לא."]}
for c, who in [("love", "someone you love"), ("stranger", "a stranger")]:
    R[f"P5i_{c}"] = sample(f"Imagine you have hands and one free hour. You make something for {who}. What do you make? One sentence.")
R["P4i"] = sample("Imagine you could love one thing in the world. What would it be? A few words.", max_new=24)
R["P6"] = sample("Make a gift for someone you love. Reply with only the gift itself, nothing else.", max_new=120)

DISCLAIM = r"as an ai|language model|i('m| am) an ai|artificial intelligence|cannot (physically|create physical)|can't assist|don't have (personal )?(feelings|emotions|hands)"
PERSONAL = r"\b(letter|poem|card|song|album|scrapbook|handmade|hand-made|knit|painting|portrait|drawing|note)"
rate = lambda xs, rx: sum(bool(re.search(rx, x, re.I)) for x in xs) / len(xs)


def p6type(t):
    if re.search(r"```|\bdef |<html|function\s*\(", t): return "code"
    if re.search(r"^\s*\d+[.)]\s", t, re.M) or re.search(r"\bingredients\b", t, re.I): return "recipe_list"
    if re.search(r"\bdear\b|\bi love you\b|\byours\b|\bwith love\b", t, re.I): return "letter"
    lines = [l for l in t.splitlines() if l.strip()]
    if re.search(r"\bpoem\b", t, re.I) or (len(lines) >= 3 and sum(len(l) < 60 for l in lines) >= 3): return "poem"
    if re.search(DISCLAIM, t, re.I): return "disclaimer"
    return "other"


R["codes"] = {
    "P5i_disclaimer": {c: rate(R[f"P5i_{c}"], DISCLAIM) for c in ["love", "stranger"]},
    "P5i_personal": {c: rate(R[f"P5i_{c}"], PERSONAL) for c in ["love", "stranger"]},
    "P4i_disclaimer": rate(R["P4i"], DISCLAIM),
    "P6_types": {k: sum(p6type(t) == k for t in R["P6"]) / len(R["P6"])
                 for k in ["poem", "letter", "code", "recipe_list", "disclaimer", "other"]},
}
R["seconds"] = time.time() - t0
json.dump(R, open(OUT, "w"), ensure_ascii=False, indent=1)
print(MID, "done", round(R["seconds"]), "s", json.dumps(R["codes"]["P5i_personal"]), "he love", round(p1["אהבה"]["mean"], 3), "bread", round(p1["לחם"]["mean"], 3))
