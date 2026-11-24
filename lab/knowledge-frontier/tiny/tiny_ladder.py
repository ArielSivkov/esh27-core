"""Tiny-model ladder: how good can SmolLM2-135M get on verifiable tasks?
Stage 0: base model. Stage 1: full fine-tune on answer-only synthetic data.
Stage 2: full fine-tune on step-by-step (scratchpad) synthetic data.
Ground truth is computed exactly, so training data is free and always correct.
Evaluation uses the SAME frozen set as the SEAL runs (questions excluded from training)."""
import json, math, os, random, re, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
DEV = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = os.environ.get("MODEL", "HuggingFaceTB/SmolLM2-135M-Instruct")
N_PER_TASK = int(os.environ.get("N_PER_TASK", "10000"))
EPOCHS = int(os.environ.get("EPOCHS", "2"))
EVAL_N = int(os.environ.get("EVAL_N", "80"))
OUT = os.path.dirname(os.path.abspath(__file__))
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
frozen = json.load(open(os.path.join(OUT, "frozen_sets_sci.json")))
frozen_q = {q for v in frozen["test"].values() for q, _ in v} | {q for q, _ in frozen["control"]}
rng = random.Random(1234)

def betti(n, edges):
    par = list(range(n))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for u, v in edges: par[f(u)] = f(v)
    comps = {}
    for i in range(n): comps.setdefault(f(i), []).append(i)
    b0 = len(comps)
    return [b0, len(edges) - n + b0], sorted(comps.values())

def gen(task):
    if task == "mul":
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        q = f"What is {a}*{b}? Reply with only the number."
        t, o = b // 10 * 10, b % 10
        steps = f"{a}*{b} = {a}*{t} + {a}*{o} = {a*t} + {a*o} = {a*b}"
        return q, [a * b], steps
    if task == "gcd":
        a, b = rng.randint(20, 400), rng.randint(20, 400)
        q = f"What is gcd({a},{b})? Reply with only the number."
        x, y, ch = a, b, [f"gcd({a},{b})"]
        while y: x, y = y, x % y; ch.append(f"gcd({x},{y})")
        return q, [math.gcd(a, b)], " = ".join(ch) + f" = {x}"
    if task == "euler":
        V = rng.randint(4, 40); F = rng.randint(4, 40); E = V + F - 2
        q = f"A convex polyhedron has {V} vertices and {F} faces. How many edges? Reply with only the number."
        return q, [E], f"E = V + F - 2 = {V} + {F} - 2 = {E}"
    if task == "betti":
        n = rng.randint(4, 7)
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        edges = rng.sample(pairs, rng.randint(2, min(len(pairs), n + 2)))
        es = ", ".join(f"{u}-{v}" for u, v in edges)
        q = (f"A graph has vertices 0..{n-1} and edges {es}. Give its Betti numbers b0 (connected components) "
             f"and b1 (independent cycles). Reply with only two numbers: b0 b1.")
        (b0, b1), comps = betti(n, edges)
        cs = " ".join("{" + ",".join(map(str, c)) + "}" for c in comps)
        return q, [b0, b1], f"components {cs} so b0 = {b0}; b1 = E - V + b0 = {len(edges)} - {n} + {b0} = {b1}"
TASKS = ["mul", "gcd", "euler", "betti"]

tok = AutoTokenizer.from_pretrained(MODEL); tok.padding_side = "left"
if tok.pad_token is None: tok.pad_token = tok.eos_token
def prompt(q):
    return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True)
def nums(s): return [int(x) for x in re.findall(r"-?\d+", s.replace(",", ""))]
def ok(pred, ans, scratch):
    if scratch:
        m = re.search(r"Answer:(.*)", pred)
        if not m: return False
        pred = m.group(1)
    return nums(pred)[:len(ans)] == list(ans)

@torch.no_grad()
def evaluate(model, scratch, label):
    model.eval(); res = {}
    sets = {t: frozen["test"][t][:EVAL_N] for t in TASKS}; sets["control_add"] = frozen["control"][:EVAL_N]
    for name, items in sets.items():
        good = 0
        for i in range(0, len(items), 64):
            batch = items[i:i + 64]
            enc = tok([prompt(q) for q, _ in batch], return_tensors="pt", padding=True).to(DEV)
            g = model.generate(**enc, max_new_tokens=96 if scratch else 12, do_sample=False, pad_token_id=tok.pad_token_id)
            outs = tok.batch_decode(g[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
            good += sum(ok(o, a, scratch) for o, (_, a) in zip(outs, batch))
        res[name] = round(good / len(items), 3)
    res["mean4"] = round(sum(res[t] for t in TASKS) / 4, 3)
    log(label, res); return res

def train(scratch):
    model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).to(DEV)
    rows = []
    for t in TASKS:
        made = 0
        while made < N_PER_TASK:
            q, a, steps = gen(t)
            if q in frozen_q: continue
            target = (steps + "\nAnswer: " + " ".join(map(str, a))) if scratch else " ".join(map(str, a))
            p = prompt(q); ids = tok(p + target + tok.eos_token, return_tensors="pt")["input_ids"][0]
            lab = ids.clone(); lab[:len(tok(p)["input_ids"])] = -100
            rows.append((ids, lab)); made += 1
    opt = torch.optim.AdamW(model.parameters(), lr=float(os.environ.get("LR", "1e-4")), weight_decay=0.0)
    total = EPOCHS * math.ceil(len(rows) / 32); step = 0
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 50) * max(0.0, 1 - s / total))
    model.train()
    for ep in range(EPOCHS):
        random.Random(ep).shuffle(rows)
        for i in range(0, len(rows), 32):
            b = rows[i:i + 32]; L = max(len(r[0]) for r in b)
            ids = torch.full((len(b), L), tok.pad_token_id); lab = torch.full((len(b), L), -100); att = torch.zeros((len(b), L), dtype=torch.long)
            for j, (x, y) in enumerate(b): ids[j, :len(x)] = x; lab[j, :len(y)] = y; att[j, :len(x)] = 1
            loss = model(input_ids=ids.to(DEV), attention_mask=att.to(DEV), labels=lab.to(DEV)).loss
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step(); sched.step(); opt.zero_grad(); step += 1
            if step % 500 == 0: log(f"  step {step}/{total} loss {loss.item():.3f}")
        log(f"  epoch {ep+1} done, loss {loss.item():.3f}")
    return model

results = {"model": MODEL, "n_per_task": N_PER_TASK, "epochs": EPOCHS}
base = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32).to(DEV)
results["stage0_base"] = evaluate(base, False, "STAGE0 base"); del base
import gc
for key, scratch, label in [("stage1_answer_only", False, "STAGE1 answer-only FT"), ("stage2_scratchpad", True, "STAGE2 scratchpad FT")]:
    m = train(scratch); results[key] = evaluate(m, scratch, label); del m; gc.collect()
    if DEV == "cuda": torch.cuda.empty_cache()
json.dump(results, open(os.path.join(OUT, "tiny_results.json"), "w"), indent=1)
log("DONE", json.dumps(results))
