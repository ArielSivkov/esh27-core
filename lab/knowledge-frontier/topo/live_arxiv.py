# Live counts from the arXiv API (independent source, includes 2022-2026). Generic UA, 4s spacing.
import urllib.request,urllib.parse,re,time,json
T=[("cond-mat.stat-mech","physics.bio-ph","quant-ph"),("math.CV","math.DG","math.PR"),("cs.CR","cs.LG","quant-ph"),
   ("cs.CL","cs.LG","physics.soc-ph"),("cond-mat.dis-nn","math.PR","quant-ph"),("cs.LG","stat.ML","cs.AI")]
def total(q):
    for k in range(5):
        try:
            u="http://export.arxiv.org/api/query?"+urllib.parse.urlencode({"search_query":q,"max_results":0})
            x=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"research-script/0.1"}),timeout=60).read().decode()
            return int(re.search(r"<opensearch:totalResults[^>]*>(\d+)<",x).group(1))
        except Exception as e:
            print("retry",q,e,flush=True); time.sleep(10*(k+1))
    return None
res=[]
for t in T:
    a,b,c=t; row={"tri":" + ".join(t)}
    for name,q in [("A",f"cat:{a}"),("AB",f"cat:{a} AND cat:{b}"),("AC",f"cat:{a} AND cat:{c}"),("BC",f"cat:{b} AND cat:{c}"),("ABC",f"cat:{a} AND cat:{b} AND cat:{c}")]:
        row[name]=total(q); time.sleep(4)
    if all(row.get(k) for k in ("A","AB","AC")):
        row["exp"]=round(row["AB"]*row["AC"]/row["A"],1); row["ratio"]=round((row["ABC"] or 0)/row["exp"],3)
    print(json.dumps(row),flush=True); res.append(row)
json.dump(res,open("live_out.json","w"),indent=1)
