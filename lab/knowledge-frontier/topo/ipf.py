# Stronger null: expected triple count given ALL three pairwise counts (max-entropy / IPF on 2x2x2 table),
# symmetric in the three categories (fixes the pivot-dependence of the crude formula).
import json,itertools,collections,math
import numpy as np
alias={"math.MP":"math-ph","math.IT":"cs.IT","stat.TH":"math.ST","eess.SY":"cs.SY","econ.GN":"q-fin.EC","cs.NA":"math.NA"}
d=json.load(open("arxiv_all_cats.json"))
P=[tuple(sorted({alias.get(x,x) for x in c})) for c in d.values() if c]; N=len(P)
cnt=collections.Counter();pair=collections.Counter()
for p in P:
    for c in p: cnt[c]+=1
    for e in itertools.combinations(p,2): pair[e]+=1
strong=[e for e,w in pair.items() if w>=300]
adj=collections.defaultdict(set)
for a,b in strong: adj[a].add(b); adj[b].add(a)
tris={tuple(sorted((a,b,c))) for a,b in strong for c in adj[a]&adj[b]}
tri=collections.Counter()
for p in P:
    for t in itertools.combinations(p,3):
        if t in tris: tri[t]+=1
def m2(x,y,nxy):
    return np.array([[N-cnt[x]-cnt[y]+nxy, cnt[y]-nxy],[cnt[x]-nxy, nxy]],float)
def ipf(a,b,c):
    Mab,Mac,Mbc=m2(a,b,pair[(a,b)]),m2(a,c,pair[(a,c)]),m2(b,c,pair[(b,c)])
    X=np.ones((2,2,2))*N/8
    for _ in range(2000):
        X*= (Mab/X.sum(2))[:,:,None]; X*=(Mac/X.sum(1))[:,None,:]; X*=(Mbc/X.sum(0))[None,:,:]
    return X[1,1,1]
def pois_cdf(k,lam):
    # log-space
    return sum(math.exp(-lam+i*math.log(lam)-math.lgamma(i+1)) for i in range(k+1))
res=[]
for t in tris:
    a,b,c=t; e=ipf(a,b,c)
    crude=pair[(a,b)]*pair[(a,c)]/cnt[a]
    res.append(dict(t=t,obs=tri[t],ipf=e,r=tri[t]/e if e>0 else None,crude=crude,p=pois_cdf(tri[t],e) if e>0 else None))
res=[x for x in res if x["ipf"]>=10]
res.sort(key=lambda x:x["r"])
print("triangles (ipf exp>=10):",len(res),"ratio<0.15:",sum(x['r']<0.15 for x in res),"ratio<0.25:",sum(x['r']<0.25 for x in res),"ratio<0.5:",sum(x['r']<0.5 for x in res),"median ratio:",round(float(np.median([x['r'] for x in res])),3))
for x in res[:40]:
    print(f"{x['r']:.3f}  {' + '.join(x['t'])}  obs={x['obs']} ipf_exp={x['ipf']:.1f} crude_exp={x['crude']:.1f} p={x['p']:.1e}")
json.dump([dict(x,t=list(x['t'])) for x in res],open("ipf_out.json","w"))
