"""Verifier-gated fine-tune of a tiny brain on CPU (in the spirit of the knowledge-frontier SEAL lab).
Training examples are SYNTHETIC photo/street jobs (seed 99); every target is the Verifier's computed answer.
Held-out: the balanced probe (seed 27, never trained on) and the 87 real city jobs.
  python brain/train_tiny.py MODEL_ID OUT_DIR [steps]"""
import json, os, random, sys, time
import torch
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from brains import TinyLMBrain, task_prompt, rule_answer, PROMPT
from transformers import AutoModelForCausalLM, AutoTokenizer
mid, out_dir = sys.argv[1], sys.argv[2]; steps = int(sys.argv[3]) if len(sys.argv) > 3 else 150
torch.manual_seed(99); rnd = random.Random(99)
def synth(n):
    js = []
    for i in range(n):
        if rnd.random() < 0.6:
            r = round(rnd.uniform(10, 60), 1)
            k = rnd.random()
            if k < 0.08: js.append({"job_kind": "photo_check", "street": "x", "r": r, "d_street": None}); continue
            d = round(r * (rnd.uniform(0.05, 0.95) if k < 0.54 else rnd.uniform(1.1, 5.0)), 1)
            js.append({"job_kind": "photo_check", "street": "x", "r": r, "d_street": d})
        else:
            js.append({"job_kind": "street_check", "street": "x", "n_nodes": 0 if rnd.random() < 0.5 else rnd.randint(1, 300)})
    return js
tok = AutoTokenizer.from_pretrained(mid); model = AutoModelForCausalLM.from_pretrained(mid, torch_dtype=torch.float32)
def example(j):
    task, facts, allowed = task_prompt(j)
    p = tok.apply_chat_template([{"role": "user", "content": PROMPT.format(task=task, facts=facts, allowed=" or ".join(allowed))}],
                                add_generation_prompt=True, tokenize=False)
    tgt = json.dumps(rule_answer(j), ensure_ascii=False) + tok.eos_token
    a = tok(p, add_special_tokens=False)["input_ids"]; b = tok(tgt, add_special_tokens=False)["input_ids"]
    return a + b, [-100] * len(a) + b
data = [example(j) for j in synth(steps * 8)]
opt = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=0.0)
model.train(); t0 = time.time()
for s in range(steps):
    batch = data[s * 8:(s + 1) * 8]; L = max(len(x) for x, _ in batch)
    ids = torch.tensor([x + [tok.eos_token_id] * (L - len(x)) for x, _ in batch])
    lab = torch.tensor([y + [-100] * (L - len(y)) for _, y in batch])
    att = torch.tensor([[1] * len(x) + [0] * (L - len(x)) for x, _ in batch])
    loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
    loss.backward(); opt.step(); opt.zero_grad()
    if s % 25 == 0 or s == steps - 1: print(f"step {s} loss {loss.item():.4f} t={time.time()-t0:.0f}s", flush=True)
model.save_pretrained(out_dir); tok.save_pretrained(out_dir)
print("saved", out_dir, "train_examples", len(data), "sec", round(time.time() - t0))
