"""Self-rewriting-weights pilot (CPU): the model generates its own training data,
a deterministic verifier keeps only correct samples, a LoRA adapter is trained on them,
and the adapter is promoted only if it beats the base on a frozen test set it never sees
and does not degrade on an unrelated control set (forgetting check).
Base weights are never modified; each round produces a separate adapter directory."""
import json, os, random, re, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, PeftModel

DEV = "cuda:0" if torch.cuda.is_available() else "cpu"
MODEL = os.environ.get("MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
OUT = os.path.dirname(os.path.abspath(__file__))
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
K = int(os.environ.get("K", "4"))  # samples per training question

def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)

rng = random.Random(int(os.environ.get("SEED", "27")))
def mul_q():
    a, b = rng.randint(10, 99), rng.randint(10, 99)
    return f"What is {a}*{b}? Reply with only the number.", [a * b]
def add_q():
    a, b = rng.randint(100, 999), rng.randint(100, 999)
    return f"What is {a}+{b}? Reply with only the number.", [a + b]
def betti(n, edges):
    # b0 = connected components (union-find), b1 = E - V + b0 (cycle rank of a graph)
    par = list(range(n))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for u, v in edges: par[f(u)] = f(v)
    b0 = len({f(i) for i in range(n)})
    return [b0, len(edges) - n + b0]
def betti_q():
    n = rng.randint(4, 7)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    edges = rng.sample(pairs, rng.randint(2, min(len(pairs), n + 2)))
    es = ", ".join(f"{u}-{v}" for u, v in edges)
    return (f"A graph has vertices 0..{n-1} and edges {es}. Give its Betti numbers b0 (connected components) "
            f"and b1 (independent cycles). Reply with only two numbers: b0 b1."), betti(n, edges)
def euler_q():
    # convex polyhedron: give two of V, E, F; Euler's formula V - E + F = 2 gives the third
    V = rng.randint(4, 40); F = rng.randint(4, 40); E = V + F - 2
    return f"A convex polyhedron has {V} vertices and {F} faces. How many edges? Reply with only the number.", [E]
def gcd_q():
    import math
    a, b = rng.randint(20, 400), rng.randint(20, 400)
    return f"What is gcd({a},{b})? Reply with only the number.", [math.gcd(a, b)]
TASKS = {"mul": mul_q, "betti": betti_q, "euler": euler_q, "gcd": gcd_q}
if os.environ.get("TASKS"): TASKS = {k: TASKS[k] for k in os.environ["TASKS"].split(",")}

# Frozen sets: written to disk once, read-only for the loop, never used for training.
frozen_path = os.path.join(OUT, "frozen_sets_sci.json")  # same seed -> same frozen set
if not os.path.exists(frozen_path):
    test = {t: [g() for _ in range(80)] for t, g in TASKS.items()}
    control = [add_q() for _ in range(80)]
    json.dump({"test": test, "control": control}, open(frozen_path, "w"))
    os.chmod(frozen_path, 0o444)
frozen = json.load(open(frozen_path))
test_keys = {q for v in frozen["test"].values() for q, _ in v}

tok = AutoTokenizer.from_pretrained(MODEL)
tok.padding_side = "left"
base = (AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32, device_map="auto") if os.environ.get("MULTI") else AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).to(DEV))
log("device map:", getattr(base, "hf_device_map", DEV))

def prompt(q):
    msgs = [{"role": "system", "content": "Reply with only the final number."},
            {"role": "user", "content": q}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

def parse(t):
    return [int(x) for x in re.findall(r"-?\d+", t.replace(",", ""))]
def ok(pred, ans):
    return parse(pred)[:len(ans)] == list(ans)

@torch.no_grad()
def generate(model, qs, sample=False, bs=32):
    outs = []
    for i in range(0, len(qs), bs):
        enc = tok([prompt(q) for q in qs[i:i + bs]], return_tensors="pt", padding=True).to(DEV)
        g = model.generate(**enc, max_new_tokens=10, do_sample=sample, temperature=1.0 if sample else None,
                           top_p=None, top_k=None, pad_token_id=tok.eos_token_id)
        outs += tok.batch_decode(g[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
    return outs

def accuracy(model, items):
    preds = generate(model, [q for q, _ in items])
    return sum(ok(p, a) for p, (_, a) in zip(preds, items)) / len(items)
def suite(model):
    r = {t: round(accuracy(model, v), 3) for t, v in frozen["test"].items()}
    r["mean"] = round(sum(r.values()) / len(r), 3)
    return r

def train_lora(model_for_round, data, out_dir):
    cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM")
    m = get_peft_model(model_for_round, cfg)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=2e-4)
    m.train()
    rows = []
    for q, ans in data:
        p = prompt(q); full = p + " ".join(map(str, ans)) + tok.eos_token
        ids = tok(full, return_tensors="pt")["input_ids"][0]
        n_p = len(tok(p)["input_ids"])
        labels = ids.clone(); labels[:n_p] = -100
        rows.append((ids, labels))
    steps = 0
    for epoch in range(2):
        rng.shuffle(rows)
        for i in range(0, len(rows), 8):
            batch = rows[i:i + 8]
            L = max(len(r[0]) for r in batch)
            ids = torch.full((len(batch), L), tok.pad_token_id); lab = torch.full((len(batch), L), -100)
            att = torch.zeros((len(batch), L), dtype=torch.long)
            for j, (x, y) in enumerate(batch):
                ids[j, :len(x)] = x; lab[j, :len(y)] = y; att[j, :len(x)] = 1
            loss = m(input_ids=ids.to(DEV), attention_mask=att.to(DEV), labels=lab.to(DEV)).loss
            loss.backward(); opt.step(); opt.zero_grad(); steps += 1
        log(f"  epoch {epoch+1} done, last loss {loss.item():.3f}, steps {steps}")
    m.eval(); m.save_pretrained(out_dir)
    return m

history = []
current = base
cur_suite, cur_ctrl = suite(current), accuracy(current, frozen["control"])
cur_test = cur_suite["mean"]
log(f"BASE  test={cur_suite}  control(add)={cur_ctrl:.3f}")
history.append({"round": 0, "test": cur_suite, "control": cur_ctrl, "promoted": True})

for r in range(1, ROUNDS + 1):
    log(f"ROUND {r}: self-generate")
    pool = []
    while len(pool) < 320:
        q = TASKS[list(TASKS)[len(pool) % len(TASKS)]]()
        if q[0] not in test_keys: pool.append(q)
    qs = [q for q, _ in pool for _ in range(K)]
    samples = generate(current, qs, sample=True)
    kept, seen = [], set()
    for (q, a), s in zip([x for x in pool for _ in range(K)], samples):
        if ok(s, a) and q not in seen:  # verifier: exact arithmetic check
            kept.append((q, a)); seen.add(q)
    log(f"  self-edits kept by verifier: {len(kept)} / {len(pool)} questions")
    adapter_dir = os.path.join(OUT, f"adapter_round{r}")
    cand = train_lora(current if r == 1 else current, kept, adapter_dir)
    ts, c = suite(cand), accuracy(cand, frozen["control"]); t = ts["mean"]
    promote = (t >= cur_test + 0.03) and (c >= cur_ctrl - 0.02)
    log(f"  CANDIDATE test={ts} mean was {cur_test:.3f}  control={c:.3f} (was {cur_ctrl:.3f})  -> {'PROMOTE' if promote else 'REJECT'}")
    history.append({"round": r, "kept": len(kept), "test": ts, "control": c, "promoted": promote})
    if promote:
        current = cand.merge_and_unload() if hasattr(cand, "merge_and_unload") else cand
        cur_test, cur_ctrl = t, c
    else:
        current = cand.unload() if hasattr(cand, "unload") else base
json.dump(history, open(os.path.join(OUT, "history_sci.json"), "w"), indent=1)
log("DONE", json.dumps(history))
