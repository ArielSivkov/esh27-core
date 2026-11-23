import json,itertools,collections,random,statistics as st
import numpy as np
alias={"math.MP":"math-ph","math.IT":"cs.IT","stat.TH":"math.ST","eess.SY":"cs.SY","econ.GN":"q-fin.EC","cs.NA":"math.NA"}
d=json.load(open("arxiv_all_cats.json"))
papers=[tuple(sorted({alias.get(x,x) for x in c})) for c in d.values() if c]
cats=sorted({c for p in papers for c in p}); idx={c:i for i,c in enumerate(cats)}
P=[[idx[c] for c in p] for p in papers]
def analyze(P,label):
    cnt=collections.Counter();pair=collections.Counter()
    for p in P:
        for c in p: cnt[c]+=1
        if len(p)>1:
            for e in itertools.combinations(sorted(p),2): pair[e]+=1
    strong=[e for e,w in pair.items() if w>=300]
    adj=collections.defaultdict(set)
    for a,b in strong: adj[a].add(b); adj[b].add(a)
    tris=set()
    for a,b in strong:
        for c in adj[a]&adj[b]: tris.add(tuple(sorted((a,b,c))))
    tri=collections.Counter()
    for p in P:
        if len(p)>2:
            for t in itertools.combinations(sorted(p),3):
                if t in tris: tri[t]+=1
    res=[]
    for t in tris:
        a,b,c=t; exp=pair[(a,b)]*pair[(a,c)]/cnt[a]
        if exp>=5: res.append((tri[t]/exp,t,tri[t],exp))
    hollow=[x for x in res if x[0]<0.15]; h20=[x for x in hollow if x[3]>=20]
    rs=[x[0] for x in res]
    out=dict(label=label,strong_pairs=len(strong),triangles=len(res),hollow=len(hollow),hollow_exp20=len(h20),max_exp_hollow=round(max([x[3] for x in hollow],default=0),1),
             median_ratio=round(st.median(rs),3) if rs else None,
             p05=round(float(np.percentile(rs,5)),3) if rs else None)
    print(out,flush=True); return out,hollow
real,real_h=analyze(P,"real")
sizes=[len(p) for p in P]; flat=np.array([c for p in P for c in p])
nulls=[]
for s in range(5):
    rng=np.random.default_rng(100+s); f=flat.copy(); rng.shuffle(f)
    Q=[];i=0;bad=0
    for k in sizes:
        q=f[i:i+k].tolist(); i+=k
        if len(set(q))<k: bad+=1
        Q.append(list(set(q)))   # duplicates collapsed (tiny effect, counted below)
    o,h=analyze(Q,f"null seed {100+s}"); o["papers_with_collapsed_dup"]=bad; nulls.append(o)
json.dump(dict(real=real,nulls=nulls,real_hollow=[(round(r,3),[cats[i] for i in t],n,round(e,1)) for r,t,n,e in sorted(real_h)]),open("nullmodel_out.json","w"),indent=1)
