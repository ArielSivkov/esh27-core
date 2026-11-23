import json,itertools,collections,re
import numpy as np
alias={"math.MP":"math-ph","math.IT":"cs.IT","stat.TH":"math.ST","eess.SY":"cs.SY","econ.GN":"q-fin.EC","cs.NA":"math.NA"}
d=json.load(open("arxiv_2026_cats.json"))
def yr(pid):
    m=re.match(r"^(\d{2})(\d{2})\.",pid) or re.search(r"/(\d{2})(\d{2})",pid); y=int(m.group(1)); return 1900+y if y>=90 else 2000+y
W={"<=2021":lambda y:y<=2021,"2022-2026":lambda y:y>=2022}
T=[("cs.CL","cs.LG","physics.soc-ph"),("cond-mat.stat-mech","physics.bio-ph","quant-ph"),("math.CV","math.DG","math.PR"),
   ("cs.CR","cs.LG","quant-ph"),("math.CO","math.NT","math.RT"),("physics.bio-ph","q-bio.NC","q-bio.QM"),("cs.LG","stat.ML","cs.AI")]
for w,f in W.items():
    P=[tuple(sorted({alias.get(x,x) for x in c})) for k,c in d.items() if f(yr(k))]; N=len(P)
    cnt=collections.Counter();pair=collections.Counter();tri=collections.Counter()
    S={tuple(sorted(t)) for t in T}
    for p in P:
        for c in p: cnt[c]+=1
        for e in itertools.combinations(p,2): pair[e]+=1
        if len(p)>2:
            for t in itertools.combinations(p,3):
                if t in S: tri[t]+=1
    def m2(x,y):
        a,b=sorted((x,y)); n=pair[(a,b)]
        return np.array([[N-cnt[x]-cnt[y]+n,cnt[y]-n],[cnt[x]-n,n]],float)
    print(f"== {w}: {N} papers")
    for t in T:
        a,b,c=sorted(t); X=np.ones((2,2,2))*N/8
        Mab,Mac,Mbc=m2(a,b),m2(a,c),m2(b,c)
        for _ in range(2000):
            X*=(Mab/X.sum(2))[:,:,None]; X*=(Mac/X.sum(1))[:,None,:]; X*=(Mbc/X.sum(0))[None,:,:]
        k=(a,b,c); e=X[1,1,1]
        print(f"  {' + '.join(k)}: pairs={pair[(a,b)]},{pair[(a,c)]},{pair[(b,c)]} obs={tri[k]} ipf_exp={e:.1f} ratio={tri[k]/e:.2f}")
