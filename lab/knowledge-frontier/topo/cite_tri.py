# Citation-based triangles: each citing work -> set of subfields it cites >=2 times (score>=0.9 map). Symmetric IPF null on 2x2x2.
import os, json, random, itertools, collections, numpy as np, pyarrow.parquet as pq, pandas as pd
from huggingface_hub import HfApi, hf_hub_download
R="Mearman/OpenAlex"; m=np.load("primary_map.npz"); W=m["work_id"]; Sf=m["subfield"]
rw=sorted(f for f in HfApi().list_repo_files(R,repo_type="dataset") if f.startswith("data/works/referenced_works/"))
random.seed(27); pick=random.sample(rw,20); P=[]
for f in pick:
    p=hf_hub_download(R,f,repo_type="dataset",local_dir="oa_refs"); t=pq.read_table(p); os.remove(p)
    a=t.column("work_id").to_numpy(); b=t.column("referenced_work_id").to_numpy()
    i=np.searchsorted(W,b); i[i>=len(W)]=0; ok=W[i]==b
    df=pd.DataFrame({"a":a[ok],"s":Sf[i[ok]]}).groupby(["a","s"]).size().reset_index(name="n")
    df=df[df.n>=2]
    P+= [tuple(sorted(g)) for g in df.groupby("a").s.apply(list) if len(g)>=1]
N=len(P); cnt=collections.Counter(); pair=collections.Counter()
for p in P:
    cnt.update(p); pair.update(itertools.combinations(p,2))
strong=[e for e,w in pair.items() if w>=300]; adj=collections.defaultdict(set)
for a,b in strong: adj[a].add(b); adj[b].add(a)
tris={tuple(sorted((a,b,c))) for a,b in strong for c in adj[a]&adj[b]}
tri=collections.Counter()
for p in P:
    if len(p)>=3:
        for t in itertools.combinations(p,3):
            if t in tris: tri[t]+=1
def m2(x,y): n=pair[(x,y)]; return np.array([[N-cnt[x]-cnt[y]+n,cnt[y]-n],[cnt[x]-n,n]],float)
def ipf(a,b,c):
    A,B,C=m2(a,b),m2(a,c),m2(b,c); X=np.ones((2,2,2))*N/8
    for _ in range(500):
        X*=(A/X.sum(2))[:,:,None]; X*=(B/X.sum(1))[:,None,:]; X*=(C/X.sum(0))[None,:,:]
    return X[1,1,1]
rows=[]
for t in tris:
    e=ipf(*t); rows.append((t,tri[t],e,(tri[t]+0.5)/(e+0.5)))
rows.sort(key=lambda r:r[3]); ratios=np.array([r[3] for r in rows])
names={d["subfield_id"]:d["display_name"] for d in json.load(open("oa_subfields.json"))}
def rep(t):
    t=tuple(sorted(t)); r=[x for x in rows if x[0]==t]
    if not r: return {"triple":[names[x] for x in t],"status":"not all 3 pairs strong (>=300)","pairs":[pair[e] for e in itertools.combinations(t,2)]}
    _,o,e,q=r[0]; return {"triple":[names[x] for x in t],"obs":o,"exp":round(e,1),"ratio":round(q,3),"percentile_low":round(float((ratios<q).mean()),3)}
res={"citing_works":N,"strong_pairs":len(strong),"triangles":len(rows),"ratio_median":round(float(np.median(ratios)),3),
 "check_A_statmech_biophys_AMO":rep((3109,1304,3107)),"check_C_biophys_cogneuro_AMO":rep((1304,2805,3107)),
 "most_hollow_10":[{"t":[names[x] for x in r[0]],"obs":r[1],"exp":round(r[2],1),"ratio":round(r[3],3)} for r in rows[:10]]}
print(json.dumps(res,indent=1,ensure_ascii=False)); json.dump(res,open("cite_tri_out.json","w"),indent=1,ensure_ascii=False)
