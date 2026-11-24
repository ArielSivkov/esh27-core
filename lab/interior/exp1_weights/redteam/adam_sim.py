# Toy: one LoRA module per layer (q: 1536->1536, v: 1536->256), r=8, scale 2, AdamW lr 2e-4, PEFT-like init
# (A kaiming-uniform a=sqrt(5), B=0). Gradients from a fixed linear "loss" pullback:
# dL/dy_t = signal (rank-s output directions shared across steps) + noise. X random tokens.
import torch, math, numpy as np
torch.manual_seed(0)
def erank(s):
    p=s/s.sum(); p=p[p>0]; return float(torch.exp(-(p*p.log()).sum()))
def run(steps, srank, snr, L=28, T=64, din=1536, outs=(1536,256), seed=0, layer_scale=None, shared_U=None):
    g=torch.Generator().manual_seed(seed)
    res=[]; layerE=[]; Us={}
    for l in range(L):
        E=0
        for mi,dout in enumerate(outs):
            A=torch.empty(8,din); bound=1/math.sqrt(din)  # kaiming_uniform(a=sqrt5) -> bound=1/sqrt(fan_in)
            A.uniform_(-bound,bound,generator=g); B=torch.zeros(dout,8)
            A.requires_grad_(); B.requires_grad_()
            opt=torch.optim.AdamW([A,B],lr=2e-4)
            U=shared_U[(l,mi)] if shared_U is not None else torch.linalg.qr(torch.randn(dout,max(srank,1),generator=g))[0]
            Us[(l,mi)]=U
            ls = layer_scale[l] if layer_scale is not None else 1.0
            for t in range(steps):
                X=torch.randn(T,din,generator=g)
                Gy = torch.randn(T,dout,generator=g)  # noise
                if srank>0: Gy = Gy + snr*(torch.randn(T,srank,generator=g)@U.T)*math.sqrt(dout/srank)
                Gy=Gy*ls*1e-3
                y=2.0*(X@A.T)@B.T
                (y*Gy).sum().backward(); opt.step(); opt.zero_grad()
            with torch.no_grad():
                dW=2.0*B@A; s=torch.linalg.svdvals(dW)[:8]
                Uw=torch.linalg.svd(dW,full_matrices=False)[0][:,:4]
            res.append((mi,erank(s),float((s**2).sum()), Uw, U))
            E+=float((s**2).sum())
        layerE.append(E)
    layerE=np.array(layerE)
    top=np.sort(layerE)[::-1][:L//4].sum()/layerE.sum()
    qshare=sum(r[2] for r in res if r[0]==0)/sum(r[2] for r in res)
    er=np.median([r[1] for r in res])
    return er, top, qshare, res, Us
for steps in (28,50):
  for srank,snr in [(0,0),(1,1),(1,5),(2,5),(4,5)]:
    er,top,qs,_,_=run(steps,srank,snr,L=8)
    print(f"steps {steps} signal rank {srank} snr {snr}: median erank {er:.2f}  q_share {qs:.3f}")
# layer gradient magnitudes differing 10x across layers: does Adam flatten the profile?
ls=np.exp(np.linspace(0,np.log(10),28))
er,top,qs,_,_=run(28,0,0,layer_scale=ls)
print("noise, grad scale 1..10x across layers: top-quarter share",round(top,3),"q_share",round(qs,3))
er,top,qs,_,_=run(28,0,0)
print("noise, equal grads: top-quarter share",round(top,3))
