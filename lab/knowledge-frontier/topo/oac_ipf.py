import json,collections,numpy as np,sys
C=json.load(open(sys.argv[1])); N=C['N']; PMIN=int(sys.argv[2])
cnt={int(k):v for k,v in C['cnt'].items()}
pair={tuple(map(int,k.split(','))):v for k,v in C['pair'].items()}
tri={tuple(map(int,k.split(','))):v for k,v in C['tri'].items()}
nm={r['concept_id']:r['display_name'] for r in json.load(open('oa_concepts_l01.json'))}
strong={e for e,w in pair.items() if w>=PMIN}
adj=collections.defaultdict(set)
for a,b in strong: adj[a].add(b); adj[b].add(a)
T={tuple(sorted((a,b,c))) for a,b in strong for c in adj[a]&adj[b]}
def m2(x,y):
    n=pair[tuple(sorted((x,y)))]; return np.array([[N-cnt[x]-cnt[y]+n,cnt[y]-n],[cnt[x]-n,n]],float)
res=[]
for t in T:
    a,b,c=t; X=np.ones((2,2,2))*N/8; A,B,Cc=m2(a,b),m2(a,c),m2(b,c)
    for _ in range(300):
        X*=(A/X.sum(2))[:,:,None]; X*=(B/X.sum(1))[:,None,:]; X*=(Cc/X.sum(0))[None,:,:]
    e=X[1,1,1]
    if e>=20: res.append((tri.get(t,0)/e,t,tri.get(t,0),e))
res.sort(); r=np.array([x[0] for x in res])
print('N',N,'multi-share',round(C['nmulti']/N,3),'triangles',len(res),'median',round(float(np.median(r)),3),'p5',round(float(np.percentile(r,5)),3),'<0.15:',int((r<0.15).sum()),'zero-obs:',int((r==0).sum()))
for x in res[:30]: print(f"{x[0]:.3f} obs={x[2]} exp={x[3]:.0f} | "+' + '.join(nm.get(s,str(s)) for s in x[1]))
json.dump([[x[0],[nm.get(s,str(s)) for s in x[1]],x[2],x[3]] for x in res],open('oac_ipf_out.json','w'),ensure_ascii=False)
