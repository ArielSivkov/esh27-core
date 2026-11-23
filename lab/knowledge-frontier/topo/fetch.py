import urllib.request, re, time, json, sys
groups=["math","cs","physics","astro-ph","cond-mat","hep-th","hep-ph","quant-ph","gr-qc","nlin","q-bio","q-fin","stat","eess","econ","math-ph","nucl-th","hep-ex"]
out={}
for g in groups:
    q=f"cat:{g}*" if g not in("hep-th","hep-ph","quant-ph","gr-qc","math-ph","nucl-th","hep-ex") else f"cat:{g}"
    url=f"https://export.arxiv.org/api/query?search_query={q}&sortBy=submittedDate&sortOrder=descending&max_results=1000"
    for attempt in range(3):
        try:
            x=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"topology-research-script/0.1"}),timeout=120).read().decode()
            break
        except Exception as e:
            print(g,'retry',e,file=sys.stderr); time.sleep(10)
    for entry in x.split("<entry>")[1:]:
        pid=re.search(r"<id>http[s]?://arxiv.org/abs/([^<]+?)(v\d+)?</id>",entry).group(1)
        cats=sorted(set(re.findall(r'<category term="([^"]+)"',entry)))
        cats=[c for c in cats if re.match(r'^[a-z\-]+(\.[A-Za-z\-]+)?$',c)]
        out[pid]=cats
    print(g,len(out),file=sys.stderr); time.sleep(3.5)
json.dump(out,open("arxiv_cats.json","w"))
print("papers",len(out))
