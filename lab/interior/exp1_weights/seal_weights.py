"""Experiment 1 (Kaggle T4): SEAL loop identical to knowledge-frontier/seal/loop_sci_gpu2.py, plus:
- torch.manual_seed(SEED); LoRA init and trained adapter saved every round;
- two control adapters from the base model (ctrl_add, ctrl_shuf), see PREREG.md;
- weight analysis (norms, effective rank, subspace overlaps, direction vs W0) written to analysis.json.
The frozen set is read from FROZEN (path); it is never trained on."""
import json, os, random, re, sys, time, math, gc
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

DEV = "cuda:0" if torch.cuda.is_available() else "cpu"
MODEL = os.environ.get("MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
OUT = os.environ.get("OUT", "/kaggle/working/exp1")
FROZEN = os.environ.get("FROZEN", "/kaggle/working/frozen_sets_sci.json")
ROUNDS = int(os.environ.get("ROUNDS", "3"))
SEEDS = [int(s) for s in os.environ.get("SEEDS", "27,28").split(",")]
K = 4
POOL = int(os.environ.get("POOL", "320"))  # questions per round (smoke tests only change this)
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
def log(*a):
    print(f"[{(time.time()-T0)/60:6.1f}m]", *a, flush=True)

frozen = json.load(open(FROZEN))
test_keys = {q for v in frozen["test"].values() for q, _ in v}
tok = AutoTokenizer.from_pretrained(MODEL); tok.padding_side = "left"

def make_tasks(rng):
    def mul_q():
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        return f"What is {a}*{b}? Reply with only the number.", [a * b]
    def add_q():
        a, b = rng.randint(100, 999), rng.randint(100, 999)
        return f"What is {a}+{b}? Reply with only the number.", [a + b]
    def betti(n, edges):
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
        V = rng.randint(4, 40); F = rng.randint(4, 40); E = V + F - 2
        return f"A convex polyhedron has {V} vertices and {F} faces. How many edges? Reply with only the number.", [E]
    def gcd_q():
        a, b = rng.randint(20, 400), rng.randint(20, 400)
        return f"What is gcd({a},{b})? Reply with only the number.", [math.gcd(a, b)]
    return {"mul": mul_q, "betti": betti_q, "euler": euler_q, "gcd": gcd_q}, add_q

def prompt(q):
    msgs = [{"role": "system", "content": "Reply with only the final number."}, {"role": "user", "content": q}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
def task_of(q):
    return "gcd" if "gcd" in q else "mul" if "*" in q else "betti" if "graph" in q else "euler" if "polyhedron" in q else "add"
def parse(t): return [int(x) for x in re.findall(r"-?\d+", t.replace(",", ""))]
def ok(pred, ans): return parse(pred)[:len(ans)] == list(ans)

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
    r = {t: round(accuracy(model, v), 4) for t, v in frozen["test"].items()}
    r["mean"] = round(sum(r.values()) / len(r), 4)
    return r

def load_base():
    return AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).to(DEV)

def lora_state(m):
    return {k: v.detach().float().cpu().clone() for k, v in m.named_parameters() if "lora_" in k}

def train_lora(model, data, out_dir, rng):
    cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM")
    m = get_peft_model(model, cfg)
    init = lora_state(m)
    torch.save(init, out_dir + "_init.pt")
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=2e-4)
    m.train(); rows = []
    for q, ans in data:
        p = prompt(q); full = p + " ".join(map(str, ans)) + tok.eos_token
        ids = tok(full, return_tensors="pt")["input_ids"][0]
        n_p = len(tok(p)["input_ids"]); labels = ids.clone(); labels[:n_p] = -100
        rows.append((ids, labels))
    steps = 0
    for epoch in range(2):
        rng.shuffle(rows)
        for i in range(0, len(rows), 8):
            batch = rows[i:i + 8]; L = max(len(r[0]) for r in batch)
            ids = torch.full((len(batch), L), tok.pad_token_id); lab = torch.full((len(batch), L), -100)
            att = torch.zeros((len(batch), L), dtype=torch.long)
            for j, (x, y) in enumerate(batch):
                ids[j, :len(x)] = x; lab[j, :len(y)] = y; att[j, :len(x)] = 1
            loss = m(input_ids=ids.to(DEV), attention_mask=att.to(DEV), labels=lab.to(DEV)).loss
            loss.backward(); opt.step(); opt.zero_grad(); steps += 1
        log(f"    epoch {epoch+1} loss {loss.item():.3f} steps {steps}")
    m.eval()
    torch.save(lora_state(m), out_dir + ".pt")
    return m, steps

# ---------------- runs ----------------
meta = {"model": MODEL, "seeds": SEEDS, "rounds": ROUNDS, "runs": {}}
W0 = None
for SEED in SEEDS:
    torch.manual_seed(SEED); rng = random.Random(SEED)
    TASKS, add_q = make_tasks(rng)
    base = load_base()
    if W0 is None:
        W0 = {k: v.detach().float().cpu().clone() for k, v in base.named_parameters()
              if k.endswith(("q_proj.weight", "v_proj.weight"))}
        torch.save(W0, os.environ.get("W0PATH", "/tmp/W0_qv.pt"))  # outside OUT: used by the analysis, not exported
    current = base
    hist = []
    cs, cc = suite(current), accuracy(current, frozen["control"])
    log(f"seed {SEED} BASE {cs} ctrl {cc:.4f}")
    hist.append({"round": 0, "test": cs, "control": cc, "promoted": True})
    cur_test, cur_ctrl = cs["mean"], cc
    r1_kept = None
    for r in range(1, ROUNDS + 1):
        pool = []
        while len(pool) < POOL:
            q = TASKS[list(TASKS)[len(pool) % len(TASKS)]]()
            if q[0] not in test_keys: pool.append(q)
        qs = [q for q, _ in pool for _ in range(K)]
        samples = generate(current, qs, sample=True)
        kept, seen = [], set()
        for (q, a), s in zip([x for x in pool for _ in range(K)], samples):
            if ok(s, a) and q not in seen: kept.append((q, a)); seen.add(q)
        if r == 1: r1_kept = list(kept)
        log(f"seed {SEED} R{r} kept {len(kept)}/{len(pool)}")
        cand, steps = train_lora(current, kept, os.path.join(OUT, f"s{SEED}_r{r}"), rng)
        ts, c = suite(cand), accuracy(cand, frozen["control"])
        promote = (ts["mean"] >= cur_test + 0.03) and (c >= cur_ctrl - 0.02)
        log(f"seed {SEED} R{r} {ts} ctrl {c:.4f} -> {'PROMOTE' if promote else 'REJECT'}")
        hist.append({"round": r, "kept": len(kept), "steps": steps, "test": ts, "control": c, "promoted": promote,
                     "kept_by_task": {t: sum(1 for q, _ in kept if task_of(q) == t) for t in TASKS}})
        if promote:
            current = cand.merge_and_unload(); cur_test, cur_ctrl = ts["mean"], c
        else:
            current = cand.unload()
    meta["runs"][str(SEED)] = hist
    json.dump(meta, open(os.path.join(OUT, "history.json"), "w"), indent=1)
    if SEED == SEEDS[0]:
        # controls from a fresh base, same hyperparameters
        del current, base, cand; gc.collect(); torch.cuda.empty_cache()
        base = load_base(); torch.manual_seed(1000 + SEED); crng = random.Random(1000 + SEED)
        _, add_c = make_tasks(crng)
        addpool = [add_c() for _ in range(max(600, 2 * POOL))]
        outs = generate(base, [q for q, _ in addpool], sample=True)
        addkept = [(q, a) for (q, a), s in zip(addpool, outs) if ok(s, a)][:len(r1_kept)]
        log(f"ctrl_add N={len(addkept)} (target {len(r1_kept)})")
        m, st = train_lora(base, addkept, os.path.join(OUT, "ctrl_add"), crng)
        meta["ctrl_add"] = {"n": len(addkept), "steps": st, "test": suite(m), "control": accuracy(m, frozen["control"])}
        log("ctrl_add", meta["ctrl_add"])
        base = m.unload(); del m; gc.collect(); torch.cuda.empty_cache()
        answers = [a for _, a in r1_kept]; crng.shuffle(answers)
        shuf = [(q, a) for (q, _), a in zip(r1_kept, answers)]
        meta["ctrl_shuf_frac_still_correct"] = sum(a == b for (_, a), (_, b) in zip(shuf, r1_kept)) / len(shuf)
        m, st = train_lora(base, shuf, os.path.join(OUT, "ctrl_shuf"), crng)
        meta["ctrl_shuf"] = {"n": len(shuf), "steps": st, "test": suite(m), "control": accuracy(m, frozen["control"])}
        log("ctrl_shuf", meta["ctrl_shuf"])
        del m, base; gc.collect(); torch.cuda.empty_cache()
    else:
        del current, base, cand; gc.collect(); torch.cuda.empty_cache()
    json.dump(meta, open(os.path.join(OUT, "history.json"), "w"), indent=1)
log("training done")

# ---------------- functional profile (PREREG amendment 1) ----------------
@torch.no_grad()
def functional_profile():
    """Per module: sum ||dW x||^2 / sum ||W0 x||^2 over prompt tokens of the frozen prompts, per task.
    Inputs x come from the base model (dW are small, so W0 inputs approximate W_{r-1} inputs)."""
    import glob
    base = load_base().eval()
    ads = {}
    for p in sorted(glob.glob(os.path.join(OUT, "*.pt"))):
        if p.endswith("_init.pt"): continue
        st = torch.load(p); n = os.path.basename(p)[:-3]; ads[n] = {}
        for k, v in st.items():
            m = re.search(r"layers\.(\d+)\.self_attn\.(q_proj|v_proj)\.lora_([AB])", k)
            if m: ads[n].setdefault((int(m.group(1)), m.group(2)), {})[m.group(3)] = v.to(DEV)
    sets = dict(frozen["test"]); sets["add_control"] = frozen["control"]
    out = {}
    for task, items in sets.items():
        acc = {}  # (adapter, layer, mod) -> [num, den]
        def mk(l):
            def hook(mod, args):
                x = args[0][mask]  # prompt tokens only (no padding)
                for mname in ("q_proj", "v_proj"):
                    W = getattr(base.model.layers[l].self_attn, mname).weight
                    den = (x @ W.T).pow(2).sum().item()
                    for n, a in ads.items():
                        A, B = a[(l, mname)]["A"], a[(l, mname)]["B"]
                        num = (2.0 * (x @ A.T) @ B.T).pow(2).sum().item()
                        e = acc.setdefault((n, l, mname), [0.0, 0.0]); e[0] += num; e[1] += den
            return hook
        hs = [base.model.layers[l].self_attn.q_proj.register_forward_pre_hook(mk(l)) for l in range(len(base.model.layers))]
        for i in range(0, len(items), 16):
            enc = tok([prompt(q) for q, _ in items[i:i + 16]], return_tensors="pt", padding=True).to(DEV)
            mask = enc["attention_mask"].bool()
            base(**enc)
        for h in hs: h.remove()
        out[task] = {f"{n}|{l}|{m}": v[0] / v[1] for (n, l, m), v in acc.items()}
    json.dump(out, open(os.path.join(OUT, "functional.json"), "w"))
    log("functional profile written")

functional_profile()
here = os.path.dirname(os.path.abspath(__file__))
os.system(f"{sys.executable} {here}/analyze_weights.py {OUT} {os.environ.get('W0PATH', '/tmp/W0_qv.pt')} | tee {OUT}/analysis_stdout.txt")
log("ALL DONE")
