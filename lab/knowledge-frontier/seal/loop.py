"""Self-rewriting-weights pilot (CPU): the model generates its own training data,
a deterministic verifier keeps only correct samples, a LoRA adapter is trained on them,
and the adapter is promoted only if it beats the base on a frozen test set it never sees
and does not degrade on an unrelated control set (forgetting check).
Base weights are never modified; each round produces a separate adapter directory."""
import json, os, random, re, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, PeftModel

torch.set_num_threads(4)
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
OUT = os.path.dirname(os.path.abspath(__file__))
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
K = 4  # samples per training question

def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)

rng = random.Random(27)
def mul_q():
    a, b = rng.randint(10, 99), rng.randint(10, 99)
    return f"{a}*{b}", a * b
def add_q():
    a, b = rng.randint(100, 999), rng.randint(100, 999)
    return f"{a}+{b}", a + b

# Frozen sets: written to disk once, read-only for the loop, never used for training.
frozen_path = os.path.join(OUT, "frozen_sets.json")
if not os.path.exists(frozen_path):
    test = [mul_q() for _ in range(150)]
    control = [add_q() for _ in range(100)]
    json.dump({"test": test, "control": control}, open(frozen_path, "w"))
    os.chmod(frozen_path, 0o444)
frozen = json.load(open(frozen_path))
test_keys = {q for q, _ in frozen["test"]}

tok = AutoTokenizer.from_pretrained(MODEL)
tok.padding_side = "left"
base = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32)

def prompt(q):
    msgs = [{"role": "system", "content": "Reply with only the final number."},
            {"role": "user", "content": f"What is {q}?"}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

def parse(t):
    m = re.search(r"-?\d[\d,]*", t)
    return int(m.group().replace(",", "")) if m else None

@torch.no_grad()
def generate(model, qs, sample=False, bs=32):
    outs = []
    for i in range(0, len(qs), bs):
        enc = tok([prompt(q) for q in qs[i:i + bs]], return_tensors="pt", padding=True)
        g = model.generate(**enc, max_new_tokens=8, do_sample=sample, temperature=1.0 if sample else None,
                           top_p=None, top_k=None, pad_token_id=tok.eos_token_id)
        outs += tok.batch_decode(g[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)
    return outs

def accuracy(model, items):
    preds = generate(model, [q for q, _ in items])
    return sum(parse(p) == a for p, (_, a) in zip(preds, items)) / len(items)

def train_lora(model_for_round, data, out_dir):
    cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"], task_type="CAUSAL_LM")
    m = get_peft_model(model_for_round, cfg)
    opt = torch.optim.AdamW([p for p in m.parameters() if p.requires_grad], lr=2e-4)
    m.train()
    rows = []
    for q, ans in data:
        p = prompt(q); full = p + str(ans) + tok.eos_token
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
            loss = m(input_ids=ids, attention_mask=att, labels=lab).loss
            loss.backward(); opt.step(); opt.zero_grad(); steps += 1
        log(f"  epoch {epoch+1} done, last loss {loss.item():.3f}, steps {steps}")
    m.eval(); m.save_pretrained(out_dir)
    return m

history = []
current = base
cur_test, cur_ctrl = accuracy(current, frozen["test"]), accuracy(current, frozen["control"])
log(f"BASE  test(mul)={cur_test:.3f}  control(add)={cur_ctrl:.3f}")
history.append({"round": 0, "test": cur_test, "control": cur_ctrl, "promoted": True})

for r in range(1, ROUNDS + 1):
    log(f"ROUND {r}: self-generate")
    pool = []
    while len(pool) < 300:
        q = mul_q()
        if q[0] not in test_keys: pool.append(q)
    qs = [q for q, _ in pool for _ in range(K)]
    samples = generate(current, qs, sample=True)
    kept, seen = [], set()
    for (q, a), s in zip([x for x in pool for _ in range(K)], samples):
        if parse(s) == a and q not in seen:  # verifier: exact arithmetic check
            kept.append((q, a)); seen.add(q)
    log(f"  self-edits kept by verifier: {len(kept)} / {len(pool)} questions")
    adapter_dir = os.path.join(OUT, f"adapter_round{r}")
    cand = train_lora(current if r == 1 else current, kept, adapter_dir)
    t, c = accuracy(cand, frozen["test"]), accuracy(cand, frozen["control"])
    promote = (t >= cur_test + 0.03) and (c >= cur_ctrl - 0.02)
    log(f"  CANDIDATE test={t:.3f} (was {cur_test:.3f})  control={c:.3f} (was {cur_ctrl:.3f})  -> {'PROMOTE' if promote else 'REJECT'}")
    history.append({"round": r, "kept": len(kept), "test": t, "control": c, "promoted": promote})
    if promote:
        current = cand.merge_and_unload() if hasattr(cand, "merge_and_unload") else cand
        cur_test, cur_ctrl = t, c
    else:
        current = cand.unload() if hasattr(cand, "unload") else base
json.dump(history, open(os.path.join(OUT, "history.json"), "w"), indent=1)
log("DONE", json.dumps(history))
