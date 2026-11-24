# Rebuild arxiv_2026_cats.json (ids from 2026: 26xx.xxxxx -> category list) from HF librarian-bots/arxiv-metadata-snapshot, reading only 2 columns.
import json, time, pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
fs=HfFileSystem(); R="datasets/librarian-bots/arxiv-metadata-snapshot/data"
t0=time.time(); out={}; total=0; newest=""
for f in sorted(fs.ls(R,detail=False)):
    if not f.endswith(".parquet"): continue
    with fs.open(f,"rb",block_size=8*2**20) as h:
        t=pq.read_table(h,columns=["id","categories"])
    ids=t.column("id").to_pylist(); cats=t.column("categories").to_pylist(); total+=len(ids)
    for i,c in zip(ids,cats):
        if i.startswith("26"):
            out[i]=c.split(); newest=max(newest,i)
    print(f.split("/")[-1],len(ids),"2026 so far",len(out),round(time.time()-t0),"s",flush=True)
json.dump(out,open("arxiv_2026_cats.json","w"))
print("total rows",total,"2026 papers",len(out),"newest id",newest,"seconds",round(time.time()-t0))
