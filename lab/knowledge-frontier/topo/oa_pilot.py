# OpenAlex via HF mirror (Mearman/OpenAlex): work = simplex on its subfields (from its <=3 topics).
import os,sys,json,itertools,collections,time
import numpy as np, pandas as pd, pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
fs=HfFileSystem(); R='datasets/Mearman/OpenAlex/data'
def tbl(d): return pd.concat([pq.read_table(fs.open(f)).to_pandas() for f in fs.glob(f'{R}/{d}/*.parquet')])
t2s=tbl('topics/subfields'); print(t2s.columns.tolist(),len(t2s))
sub=tbl('subfields/main')[['subfield_id','display_name','works_count']]
s2f=tbl('subfields/fields'); fld=tbl('fields/main')[['field_id','display_name']]
t2s=dict(zip(t2s.iloc[:,0],t2s.iloc[:,1]))
files=sorted(fs.ls(f'{R}/works/topics',detail=True),key=lambda f:f['name'])
step=int(sys.argv[1]) if len(sys.argv)>1 else 20
pick=files[::step]; print('files',len(pick),'of',len(files),'GB',sum(f['size'] for f in pick)/1e9,flush=True)
N=0;cnt=collections.Counter();pair=collections.Counter();tri=collections.Counter();t0=time.time()
for i,f in enumerate(pick):
    df=pq.read_table(fs.open(f['name']),columns=['work_id','topic_id']).to_pandas()
    df['s']=df.topic_id  # mirror stores subfield ids in this column (verified: 252/252 match subfields, 0 match topics)
    g=df.groupby('work_id').s.agg(lambda x: tuple(sorted(set(x))))
    vc=g.value_counts()
    for p,k in vc.items():
        N+=k
        for c in p: cnt[c]+=k
        for e in itertools.combinations(p,2): pair[e]+=k
        for t in itertools.combinations(p,3): tri[t]+=k
    if i%10==0: print(i,N,round(time.time()-t0),flush=True)
json.dump(dict(N=N,cnt={str(k):v for k,v in cnt.items()},pair={f'{a},{b}':v for (a,b),v in pair.items()},tri={','.join(map(str,t)):v for t,v in tri.items()}),open(f'oa_counts_step{step}.json','w'))
sub.to_json('oa_subfields.json',orient='records'); s2f.merge(fld,on='field_id').to_json('oa_sub2field.json',orient='records')
print('done N',N,'subfields',len(cnt),'pairs',len(pair),'tris',len(tri))
