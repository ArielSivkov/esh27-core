import json,itertools,collections
alias={"math.MP":"math-ph","math.IT":"cs.IT","stat.TH":"math.ST","eess.SY":"cs.SY","econ.GN":"q-fin.EC","cs.NA":"math.NA"}
d=json.load(open("arxiv_all_cats.json"))
P=[tuple(sorted({alias.get(x,x) for x in c})) for c in d.values() if c]
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
res=[]
for t in tris:
    a,b,c=t; exp=pair[(a,b)]*pair[(a,c)]/cnt[a]
    if exp>=20: res.append((tri[t]/exp,t,tri[t],round(exp),min(pair[(a,b)],pair[(a,c)],pair[(b,c)])))
res.sort()
for r in res[:45]: print(round(r[0],3),' + '.join(r[1]),r[2],r[3],'minpair',r[4])
print('total',len(res),'below .15',sum(r[0]<.15 for r in res),'below .25',sum(r[0]<.25 for r in res))
