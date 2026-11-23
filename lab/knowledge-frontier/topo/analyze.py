import json, itertools, collections, sys
import numpy as np
from ripser import ripser
d=json.load(open(sys.argv[1] if len(sys.argv)>1 else "arxiv_cats.json"))
papers=[tuple(c) for c in d.values() if c]
N=len(papers)
cnt=collections.Counter(c for p in papers for c in p)
setcnt=collections.Counter(papers)
print("papers",N,"categories",len(cnt),"multi-category papers",sum(len(p)>1 for p in papers),
      f"({100*sum(len(p)>1 for p in papers)/N:.1f}%)")

def gf2_rank(rows):
    # rows: list of python ints (bitsets); gaussian elimination over GF(2)
    piv={}; r=0
    for v in rows:
        while v:
            h=v.bit_length()-1
            if h in piv: v^=piv[h]
            else: piv[h]=v; r+=1; break
    return r

def betti(simplex_sets, maxdim=2):
    # closure of simplices up to dimension maxdim+1
    faces=[set() for _ in range(maxdim+2)]
    for s in simplex_sets:
        for k in range(1,min(len(s),maxdim+2)+1):
            for f in itertools.combinations(s,k): faces[k-1].add(f)
    idx=[{f:i for i,f in enumerate(sorted(F))} for F in faces]
    ranks=[0]
    for k in range(1,maxdim+2):
        rows=[]
        for f in idx[k]:
            v=0
            for j in range(len(f)):
                v|=1<<idx[k-1][f[:j]+f[j+1:]]
            rows.append(v)
        ranks.append(gf2_rank(rows))
    ranks.append(0)
    b=[len(idx[k])-ranks[k]-ranks[k+1] for k in range(maxdim+1)]
    return b,[len(F) for F in faces]

print("\n[1] The arXiv complex: each paper's category set is a simplex (GF(2) homology)")
for kmin in (1,2,5,10,25):
    S=[s for s,c in setcnt.items() if c>=kmin]
    # also require each face counted: use sets appearing >= kmin times
    b,f=betti(S)
    print(f"  sets seen >= {kmin:>2}: vertices={f[0]:>4} edges={f[1]:>5} triangles={f[2]:>5}  b0={b[0]} b1={b[1]} b2={b[2]}")

print("\n[2] Persistent homology of the clique (Rips) filtration, Jaccard distance between categories")
cats=[c for c,n in cnt.items() if n>=30]
ix={c:i for i,c in enumerate(cats)}
pair=collections.Counter()
for p in papers:
    q=[c for c in p if c in ix]
    for a,b2 in itertools.combinations(q,2): pair[(a,b2)]+=1
n=len(cats); D=np.ones((n,n)); np.fill_diagonal(D,0)
for (a,b2),w in pair.items():
    i,j=ix[a],ix[b2]; jac=w/(cnt[a]+cnt[b2]-w); D[i,j]=D[j,i]=1-jac
res=ripser(D,distance_matrix=True,maxdim=2)["dgms"]
print("  categories with >=30 papers:",n)
for k,dg in enumerate(res):
    fin=dg[np.isfinite(dg[:,1])]
    life=fin[:,1]-fin[:,0]
    print(f"  H{k}: {len(dg)} classes, infinite {int(np.sum(~np.isfinite(dg[:,1])))}, longest finite lifetimes {np.round(np.sort(life)[::-1][:5],3).tolist()}")
# representative longest H1 loops: report by greedy cycle near the birth threshold
dg1=res[1]
if len(dg1):
    order=np.argsort(-(dg1[:,1]-dg1[:,0]))[:5]
    print("\n[3] Longest-lived 1-dim holes (birth -> death in Jaccard distance), and the categories whose edges appear at the birth scale")
    for o in order:
        bth,dth=dg1[o]
        E=[(cats[i],cats[j]) for i in range(n) for j in range(i+1,n) if abs(D[i,j]-bth)<1e-9]
        print(f"  hole born {bth:.3f} dies {dth:.3f} (life {dth-bth:.3f}); edge(s) closing the loop at birth: {E[:3]}")
print("\n[4] Bridges: categories with highest share of cross-archive co-listings")
arch=lambda c:c.split('.')[0]
cross=collections.Counter(); tot=collections.Counter()
for p in papers:
    for c in p:
        tot[c]+=1
        if any(arch(o)!=arch(c) for o in p if o!=c): cross[c]+=1
top=sorted([c for c in tot if tot[c]>=50],key=lambda c:-cross[c]/tot[c])[:10]
print("  ",[(c,round(cross[c]/tot[c],2),tot[c]) for c in top])
