# Independent recount from the RAW HF file (fresh parser, not the cached json).
import gzip,json,math,re,collections,sys
F="/root/.cache/huggingface/hub/datasets--gfissore--arxiv-abstracts-2021/snapshots/e4c5fbd4dec8e46a5dc869216fe1c94cc585757a/arxiv-abstracts.jsonl.gz"
alias={"math.MP":"math-ph","math.IT":"cs.IT","stat.TH":"math.ST","eess.SY":"cs.SY","econ.GN":"q-fin.EC","cs.NA":"math.NA"}
T=[("cond-mat.stat-mech","physics.bio-ph","quant-ph"),("math.CV","math.DG","math.PR"),("cs.CR","cs.LG","quant-ph"),
   ("cs.CL","cs.LG","physics.soc-ph"),("cond-mat.dis-nn","math.PR","quant-ph"),("math.CV","math.DG","math.FA"),
   ("cs.GT","cs.LG","cs.LO"),("cond-mat.quant-gas","cond-mat.stat-mech","nlin.PS"),
   # controls (expected to be normal/full)
   ("cs.LG","stat.ML","cs.AI"),("hep-th","gr-qc","astro-ph.CO"),("math.PR","math-ph","cond-mat.stat-mech")]
cats_all=set(c for t in T for c in t)
single=collections.Counter(); pair=collections.Counter(); triple=collections.Counter()
single3=collections.Counter(); pair3=collections.Counter(); triple3=collections.Counter()
titles=collections.defaultdict(list); n=0; raw_example=None
for line in gzip.open(F,"rt"):
    r=json.loads(line); n+=1
    c=r["categories"]
    if isinstance(c,list): c=" ".join(c)
    cs={alias.get(x,x) for x in re.findall(r"[A-Za-z\-]+(?:\.[A-Za-z\-]+)?",c)}
    if raw_example is None: raw_example=(r.get("id"),r["categories"])
    S=cs&cats_all
    big=len(cs)>=3
    for x in S:
        single[x]+=1; single3[x]+=big
    for t in T:
        a,b,cc=t
        for u,v in ((a,b),(a,cc),(b,cc)):
            if u in cs and v in cs: pair[(t,u,v)]+=1; pair3[(t,u,v)]+=big
        if a in cs and b in cs and cc in cs:
            triple[t]+=1; triple3[t]+=big
            if len(titles[t])<25: titles[t].append((r.get("id"),r["title"].replace("\n"," ")[:140]))
def poisson_cdf(k,lam):
    s=0;term=math.exp(-lam)
    for i in range(k+1):
        s+=term; term*=lam/(i+1)
    return s
out=[]
for t in T:
    a,b,c=t
    ab,ac,bc=pair[(t,a,b)],pair[(t,a,c)],pair[(t,b,c)]
    exps=[ab*ac/single[a], ab*bc/single[b], ac*bc/single[c]]
    obs=triple[t]
    # P(C | A&B) vs P(C | A), P(C | B)
    pc_ab=obs/ab; pc_a=ac/single[a]; pc_b=bc/single[b]
    ab3,ac3=pair3[(t,a,b)],pair3[(t,a,c)]
    exp3=ab3*ac3/max(single3[a],1)
    row=dict(tri=" + ".join(t),N=single[a],A=single[a],B=single[b],C=single[c],AB=ab,AC=ac,BC=bc,ABC=obs,
             exp_by_pivot=[round(e,1) for e in exps],ratio_by_pivot=[round(obs/e,3) for e in exps],
             p_poisson_max_exp=f"{poisson_cdf(obs,max(exps)):.1e}",p_poisson_min_exp=f"{poisson_cdf(obs,min(exps)):.1e}",
             P_C_given_AB=round(pc_ab,4),P_C_given_A=round(pc_a,4),P_C_given_B=round(pc_b,4),
             only_papers_with_3plus_cats=dict(ABC=triple3[t],exp=round(exp3,1),ratio=round(triple3[t]/exp3,3) if exp3 else None))
    out.append(row); print(json.dumps(row,ensure_ascii=False))
print("papers read:",n,"example raw record:",raw_example)
json.dump(dict(rows=out,titles={" + ".join(k):v for k,v in titles.items()}),open("verify_out.json","w"),indent=1,ensure_ascii=False)
