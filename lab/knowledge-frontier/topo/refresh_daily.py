# Daily freshness: pull arXiv RSS for every category (new + cross-listed), append unseen papers to arxiv_daily.jsonl.
import json,re,time,urllib.request,os,collections
d=json.load(open("arxiv_2026_cats.json")) if os.path.exists("arxiv_2026_cats.json") else {}
cats=sorted({c for v in d.values() for c in v if '.' in c or c in ('hep-th','hep-ph','hep-ex','hep-lat','gr-qc','quant-ph','math-ph','nucl-th','nucl-ex','astro-ph','cond-mat','nlin','physics')})
seen=set()
if os.path.exists("arxiv_daily.jsonl"):
    for l in open("arxiv_daily.jsonl"): seen.add(json.loads(l)["id"])
new=0; fail=[]; dates=collections.Counter()
with open("arxiv_daily.jsonl","a") as out:
    for c in cats:
        try:
            x=urllib.request.urlopen(urllib.request.Request(f"https://export.arxiv.org/rss/{c}",headers={"User-Agent":"research-script/0.1"}),timeout=40).read().decode()
        except Exception as e:
            fail.append(c); continue
        pd=(re.findall(r"<pubDate>(.*?)</pubDate>",x) or ["?"])[0]
        for it in re.findall(r"<item>(.*?)</item>",x,re.S):
            m=re.search(r"arxiv\.org/abs/([^<\s\"]+)",it)
            if not m: continue
            pid=re.sub(r"v\d+$","",m.group(1))
            if pid in seen or pid in d: continue
            seen.add(pid); new+=1; dates[pd]+=1
            out.write(json.dumps({"id":pid,"cats":re.findall(r"<category>(.*?)</category>",it),"feed_date":pd})+"\n")
        time.sleep(1)
print(f"categories {len(cats)}, new papers {new}, total in daily file {len(seen)}, failed {len(fail)} {fail[:5]}, feed dates {dict(dates)}")
