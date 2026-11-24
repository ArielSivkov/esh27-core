import json, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
M="Qwen/Qwen2.5-0.5B-Instruct"
tok=AutoTokenizer.from_pretrained(M); tok.padding_side="left"
fr=json.load(open('/home/user/esh27-core/lab/interior/exp1_weights/frozen_sets_sci.json'))
def prompt(q):
    return tok.apply_chat_template([{"role":"system","content":"Reply with only the final number."},{"role":"user","content":q}],tokenize=False,add_generation_prompt=True)
# shared tokens: tokens of the template outside the question
def ids(q): return tok(prompt(q))["input_ids"]
for t,items in list(fr["test"].items())+[("add",fr["control"])]:
    L=[len(ids(q)) for q,_ in items]; Lq=[len(tok(q)["input_ids"]) for q,_ in items]
    fixed=len(ids(""))  # template w/o question
    print(t,"mean prompt toks",sum(L)/len(L),"question toks",sum(Lq)/len(Lq),"template toks",fixed)
# tokens that differ between gcd and add question text
q1=fr["test"]["gcd"][0][0]; q2=fr["control"][0][0]
print(tok.tokenize(q1)); print(tok.tokenize(q2))
# answer token lengths
for t,items in list(fr["test"].items())+[("add",fr["control"])]:
    a=[len(tok(" ".join(map(str,ans))+tok.eos_token)["input_ids"]) for _,ans in items]
    print(t,"answer+eos toks",sum(a)/len(a))
# hook check: q/v inputs identical
m=AutoModelForCausalLM.from_pretrained(M,dtype=torch.float32).eval()
cap={}
a=m.model.layers[3].self_attn
a.q_proj.register_forward_pre_hook(lambda mod,args: cap.__setitem__('q',args[0].clone()))
a.v_proj.register_forward_pre_hook(lambda mod,args: cap.__setitem__('v',args[0].clone()))
enc=tok([prompt(q1),prompt(q2+" extra words here")],return_tensors="pt",padding=True)
with torch.no_grad(): m(**enc)
print("q==v input:",torch.equal(cap['q'],cap['v']), cap['q'].shape, "mask sum",enc['attention_mask'].sum().item())
x=cap['q'][enc['attention_mask'].bool()]; print("masked x",x.shape)
