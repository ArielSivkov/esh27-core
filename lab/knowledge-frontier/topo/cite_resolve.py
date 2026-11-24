# Resolve rate of citations against primary_map (score>=0.9) on 20 random referenced_works files; same-subfield / same-field agreement.
import os, json, random, time, numpy as np, pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download
R="Mearman/OpenAlex"; m=np.load("primary_map.npz"); W=m["work_id"]; Sf=m["subfield"]
fld={d["subfield_id"]:d["field_id"] for d in json.load(open("oa_sub2field.json"))}
F=np.zeros(4000,np.int16)
for k,v in fld.items(): F[k]=v
def look(ids):
    i=np.searchsorted(W,ids); i[i>=len(W)]=0; ok=W[i]==ids; return ok, Sf[i]
rw=sorted(f for f in HfApi().list_repo_files(R,repo_type="dataset") if f.startswith("data/works/referenced_works/"))
random.seed(27); pick=random.sample(rw,20); t0=time.time()
E=0; Eres=0; Eboth=0; same_sub=0; same_fld=0; citing=set(); citing_ok=0; per=[]
for f in pick:
    p=hf_hub_download(R,f,repo_type="dataset",local_dir="oa_refs"); t=pq.read_table(p); os.remove(p)
    a=t.column("work_id").to_numpy(); b=t.column("referenced_work_id").to_numpy(); E+=len(a)
    okb,sb=look(b); oka,sa=look(a); Eres+=okb.sum(); both=oka&okb; Eboth+=both.sum()
    same_sub+=(sa[both]==sb[both]).sum(); same_fld+=(F[sa[both]]==F[sb[both]]).sum()
    import pandas as pd
    df=pd.DataFrame({"a":a,"ok":okb}).groupby("a").ok.agg(["sum","count"]); per.append(df)
per=pd.concat(per); 
res={"ref_files":20,"citation_edges":int(E),"cited_resolved":int(Eres),"resolve_rate":round(Eres/E,4),
     "edges_both_ends_resolved":int(Eboth),"same_subfield_share":round(same_sub/max(Eboth,1),4),"same_field_share":round(same_fld/max(Eboth,1),4),
     "citing_works":int(len(per)),"citing_with_ge3_resolved":int((per["sum"]>=3).sum()),"share_citing_ge3":round(float((per["sum"]>=3).mean()),4),
     "median_refs_per_citing":float(per["count"].median()),"seconds":round(time.time()-t0)}
print(json.dumps(res,indent=1)); json.dump(res,open("cite_resolve_out.json","w"),indent=1)
