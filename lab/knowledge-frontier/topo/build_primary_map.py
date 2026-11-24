# Full works/topics -> primary subfield for works whose top score >= 0.9. Output: primary_map.npz (sorted work_id, subfield int16).
import os, time, json, numpy as np, pyarrow.parquet as pq, pyarrow.compute as pc
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import HfApi, hf_hub_download
R="Mearman/OpenAlex"; OUT="oa_full"; os.makedirs(OUT,exist_ok=True)
tp=sorted(f for f in HfApi().list_repo_files(R,repo_type="dataset") if f.startswith("data/works/topics/"))
def one(f):
    p=hf_hub_download(R,f,repo_type="dataset",local_dir=OUT)
    df=pq.read_table(p).to_pandas(); os.remove(p)
    top=df.sort_values("score",ascending=False).drop_duplicates("work_id")
    n=len(top); top=top[top.score>=0.9]
    return n, top.work_id.to_numpy(np.int64), top.topic_id.to_numpy(np.int16)
t0=time.time(); W=[]; S=[]; nall=0
with ThreadPoolExecutor(4) as ex:
    for k,(n,w,s) in enumerate(ex.map(one,tp)):
        nall+=n; W.append(w); S.append(s)
        if k%100==0: print(k,len(tp),"works",nall,"kept",sum(len(x) for x in W),round(time.time()-t0),"s",flush=True)
w=np.concatenate(W); s=np.concatenate(S); o=np.argsort(w); w,s=w[o],s[o]
u,first=np.unique(w,return_index=True)
np.savez("primary_map.npz",work_id=w[first],subfield=s[first])
res={"files":len(tp),"works_with_any_topic":int(nall),"works_kept_score_ge_0.9":int(len(u)),"share_kept":round(len(u)/max(nall,1),4),"seconds":round(time.time()-t0)}
print(json.dumps(res)); json.dump(res,open("primary_map_out.json","w"))
