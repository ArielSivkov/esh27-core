# OpenAlex concepts (multi-label tagger, not the 3-nearest-topics classifier): work = simplex on its level-1 concepts with score>=TH.
import sys,json,itertools,collections,time
import pandas as pd, pyarrow.parquet as pq, pyarrow.compute as pc
from huggingface_hub import HfFileSystem
fs=HfFileSystem(); R='datasets/Mearman/OpenAlex/data'
step=int(sys.argv[1]); TH=float(sys.argv[2])
cm=pd.concat([pq.read_table(fs.open(f),columns=['concept_id','display_name','level','works_count']).to_pandas() for f in fs.glob(R+'/concepts/main/*.parquet')])
cm[cm.level<=1].to_json('oa_concepts_l01.json',orient='records')
files=sorted(fs.ls(R+'/works/concepts',detail=True),key=lambda f:f['name'])[::step]
print('files',len(files),'GB',round(sum(f['size'] for f in files)/1e9,2),flush=True)
N=0;nmulti=0;cnt=collections.Counter();pair=collections.Counter();tri=collections.Counter();t0=time.time()
for i,f in enumerate(files):
    t=pq.read_table(fs.open(f['name']))
    t=t.filter(pc.and_(pc.equal(t['level'],1),pc.greater_equal(t['score'],TH)))
    df=t.select(['work_id','concept_id']).to_pandas()
    g=df.groupby('work_id').concept_id.agg(lambda x: tuple(sorted(set(x))))
    for p,k in g.value_counts().items():
        N+=k; nmulti+=k*(len(p)>1)
        for c in p: cnt[c]+=k
        for e in itertools.combinations(p,2): pair[e]+=k
        for tt in itertools.combinations(p,3): tri[tt]+=k
    if i%10==0: print(i,N,round(time.time()-t0),flush=True)
json.dump(dict(N=N,nmulti=nmulti,cnt={str(k):v for k,v in cnt.items()},pair={f'{a},{b}':v for (a,b),v in pair.items()},tri={','.join(map(str,x)):v for x,v in tri.items()}),open(f'oac_counts_s{step}_t{TH}.json','w'))
print('done N',N,'multi',nmulti,'concepts',len(cnt),'pairs',len(pair),'tris',len(tri))
