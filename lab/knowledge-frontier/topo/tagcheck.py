import json,random,pyarrow.parquet as pq,pyarrow.compute as pc,pandas as pd
from huggingface_hub import HfFileSystem
fs=HfFileSystem(); R='datasets/Mearman/OpenAlex/data'
cm={r['display_name']:r['concept_id'] for r in json.load(open('oa_concepts_l01.json'))}
PAIRS=[('Acoustics','Remote sensing'),('Archaeology','Physical geography'),('Nuclear magnetic resonance','Optics'),('Quantum mechanics','Biophysics')]
mainfiles=sorted(fs.ls(R+'/works/main',detail=False)); print('main files',len(mainfiles), mainfiles[:2])
cfiles=sorted(fs.ls(R+'/works/concepts',detail=False))
out={p:[] for p in PAIRS}; rng=random.Random(7); order=list(range(len(cfiles))); rng.shuffle(order)
for i in order[:40]:
    cf=cfiles[i]; t=pq.read_table(fs.open(cf)).to_pandas(); t=t[t.level==1]
    piv=t.pivot_table(index='work_id',columns='concept_id',values='score',aggfunc='max')
    need={}
    for p in PAIRS:
        a,b=cm[p[0]],cm[p[1]]
        if a in piv and b in piv:
            s=piv[[a,b]].dropna()
            for w,row in s.iterrows():
                if len(out[p])+len(need.get(p,[]))<30: need.setdefault(p,[]).append((w,round(row[a],2),round(row[b],2)))
    if not need: continue
    mf=cf.replace('/works/concepts/','/works/main/')
    if not fs.exists(mf): print('no main for',mf); continue
    m=pq.read_table(fs.open(mf),columns=['work_id','title','publication_year']).to_pandas().set_index('work_id')
    for p,L in need.items():
        for w,sa,sb in L:
            if w in m.index: out[p].append((int(w),int(m.loc[w,'publication_year']) if pd.notna(m.loc[w,'publication_year']) else None,sa,sb,str(m.loc[w,'title'])[:130]))
    if all(len(v)>=30 for v in out.values()): break
json.dump({' + '.join(k):v for k,v in out.items()},open('tagcheck_out.json','w'),ensure_ascii=False,indent=0)
for k,v in out.items(): print(k,len(v))
