import json,itertools,collections,re,statistics as st
alias={"math.MP":"math-ph","math.IT":"cs.IT","stat.TH":"math.ST","eess.SY":"cs.SY","econ.GN":"q-fin.EC","cs.NA":"math.NA"}
d=json.load(open("arxiv_all_cats.json"))
def year(pid):
    m=re.match(r"^(\d{2})(\d{2})\.",pid) or re.search(r"/(\d{2})(\d{2})",pid)
    yy=int(m.group(1)); return 1900+yy if yy>=90 else 2000+yy
by=collections.defaultdict(list)
for pid,c in d.items():
    if c: by[year(pid)].append(tuple(sorted({alias.get(x,x) for x in c})))
print("papers per year (2015-2021):",{y:len(by[y]) for y in range(2015,2022)})
def counts(years):
    cnt=collections.Counter();pair=collections.Counter();tri=collections.Counter()
    for y in years:
        for p in by[y]:
            for c in p: cnt[c]+=1
            for e in itertools.combinations(p,2): pair[e]+=1
            for t in itertools.combinations(p,3): tri[t]+=1
    return cnt,pair,tri
def ratio(t,cnt,pair,tri):
    a,b,c=t; exp=pair[(a,b)]*pair[(a,c)]/max(cnt[a],1)
    return tri[t]/exp if exp>0 else None, exp
rows=[]
for Y in (2012,2014,2016):
    past=counts(range(Y-4,Y+1)); fut=counts(range(Y+1,Y+5))
    cnt,pair,tri=past
    strong=[e for e,w in pair.items() if w>=100]
    adj=collections.defaultdict(set)
    for a,b in strong: adj[a].add(b); adj[b].add(a)
    tris=set()
    for a,b in strong:
        for c in adj[a]&adj[b]: tris.add(tuple(sorted((a,b,c))))
    res=[]
    for t in tris:
        r0,e0=ratio(t,*past); r1,e1=ratio(t,*fut)
        if r0 is None or r1 is None or e0<5 or e1<5: continue
        res.append((r0,r1,t))
    hollow=[x for x in res if x[0]<0.15]; normal=[x for x in res if 0.5<=x[0]<=2]
    fill=lambda L:sum(1 for x in L if x[1]>=0.5)/len(L) if L else float('nan')
    print(f"\nwindow {Y-4}-{Y} -> {Y+1}-{Y+4}: triangles={len(res)} hollow(ratio<0.15)={len(hollow)} normal(0.5-2)={len(normal)}")
    print(f"  share 'filled' later (future ratio>=0.5): hollow {fill(hollow):.2f}  normal {fill(normal):.2f}")
    print(f"  median future ratio: hollow {st.median([x[1] for x in hollow]):.3f}  normal {st.median([x[1] for x in normal]):.3f}")
    filled=sorted([x for x in hollow if x[1]>=0.5],key=lambda x:-x[1])[:6]
    print("  hollow that filled:",[(x[2],round(x[0],2),round(x[1],2)) for x in filled])
    stay=sorted(hollow,key=lambda x:x[1])[:4]
    print("  hollow that stayed hollow:",[(x[2],round(x[0],2),round(x[1],2)) for x in stay])
    rows.append((Y,len(res),len(hollow),fill(hollow),fill(normal)))
json.dump(rows,open("timetest_rows.json","w"))
