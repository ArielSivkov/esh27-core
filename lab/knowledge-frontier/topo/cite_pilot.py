# Feasibility pilot for the citation-based map (log entry 8 next step). Usage: python cite_pilot.py OUTDIR
import sys, time, random, json, collections
import numpy as np, pyarrow.parquet as pq, pyarrow.compute as pc
from huggingface_hub import HfApi, hf_hub_download
R="Mearman/OpenAlex"; OUT=sys.argv[1]; api=HfApi()
fs=api.list_repo_files(R,repo_type="dataset")
tp=sorted(f for f in fs if f.startswith("data/works/topics/"))
rw=sorted(f for f in fs if f.startswith("data/works/referenced_works/"))
topics_tab=[f for f in fs if f.startswith("data/topics/") and f.endswith(".parquet")]
random.seed(27); pick=random.sample(tp,8)
t0=time.time(); nbytes=0; prim={}
for f in pick:
    p=hf_hub_download(R,f,repo_type="dataset",local_dir=OUT); import os; nbytes+=os.path.getsize(p)
    t=pq.read_table(p).to_pandas()
    top=t.sort_values("score",ascending=False).drop_duplicates("work_id")
    for w,tid,s in zip(top.work_id,top.topic_id,top.score): prim[w]=(tid,s)
dt=time.time()-t0
sc=np.array([s for _,s in prim.values()])
res={"topics_files_sampled":len(pick),"MB":round(nbytes/1e6,1),"seconds":round(dt,1),"MB_per_s":round(nbytes/1e6/dt,2),
     "works_with_topic":len(prim),"top_score_quantiles":{q:round(float(np.quantile(sc,q)),3) for q in (0.05,0.25,0.5,0.75)},
     "share_top_score_ge_0.9":round(float((sc>=0.9).mean()),3),"share_top_score_lt_0.5":round(float((sc<0.5).mean()),3)}
# topic -> subfield table
tt=[f for f in topics_tab if "/topics/" in f][:5]; res["topics_table_files"]=tt
for f in tt[:1]:
    p=hf_hub_download(R,f,repo_type="dataset",local_dir=OUT); s=pq.read_schema(p); res["topics_table_schema"]=str(s)[:600]
# references of the same sampled partitions: how many cited ids fall inside the sampled topic map (coverage of a random 8/2127 sample)
same=[f.replace("/topics/","/referenced_works/") for f in pick[:2]]
n=0; hit=0
for f in same:
    p=hf_hub_download(R,f,repo_type="dataset",local_dir=OUT); r=pq.read_table(p)
    ids=r.column("referenced_work_id").to_numpy(); n+=len(ids); hit+=sum(1 for x in ids if x in prim)
res["refs_checked"]=n; res["refs_resolved_by_sample"]=hit; res["resolve_rate"]=round(hit/max(n,1),4)
res["full_topics_GB"]=6.64; res["est_full_download_min"]=round(6640/max(res["MB_per_s"],0.01)/60,1)
print(json.dumps(res,indent=1)); json.dump(res,open(OUT+"/cite_pilot_out.json","w"),indent=1)
