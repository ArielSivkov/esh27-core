"""Build city_data.json for the agent city (v0) from the twin world's Ashdod tiles + route photos (read-only inputs).
Usage: python build_city.py TILES_DIR route_photos.json commons.csv OUT.json"""
import json, glob, os, sys, math, csv, collections
tiles_dir, photos_path, commons_path, out = sys.argv[1:5]
Q = 10.0  # coord_q: 0.1 m units
def dec(o, r):
    x, y = r[0], r[1]; pts = [(o[0] + x / Q, o[1] + y / Q)]
    for i in range(2, len(r) - 1, 2):
        x += r[i]; y += r[i + 1]; pts.append((o[0] + x / Q, o[1] + y / Q))
    return pts
B, R = [], []
for f in sorted(glob.glob(os.path.join(tiles_dir, "*.json"))):
    d = json.load(open(f)); o = d["o"]
    for b in d["b"]:
        ring = dec(o, b["r"][0])
        cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
        B.append({"id": b["i"], "n": b.get("n", ""), "t": b.get("t", ""), "a": b.get("a", 0), "h": b.get("h", 0) / 10,
                  "f": b.get("f"), "src": b.get("src", ""), "c": [round(cx, 1), round(cy, 1)],
                  "p": [[round(p[0] - cx, 1), round(p[1] - cy, 1)] for p in ring]})
    for rd in d["rd"]:
        R.append({"n": rd.get("n", ""), "c": rd.get("c"), "pts": [[round(x, 1), round(y, 1)] for x, y in dec(o, rd["r"])]})
# road graph: snap vertices to 1 m
key = lambda p: (round(p[0]), round(p[1]))
nodes, idx, edges = [], {}, collections.defaultdict(dict)
def nid(p):
    k = key(p)
    if k not in idx: idx[k] = len(nodes); nodes.append([k[0], k[1]])
    return idx[k]
for ri, rd in enumerate(R):
    prev = None
    for p in rd["pts"]:
        n = nid(p)
        if prev is not None and prev != n:
            w = math.dist(nodes[prev], nodes[n]); edges[prev][n] = w; edges[n][prev] = w
        prev = n
# keep largest connected component
seen, comps = set(), []
for s in range(len(nodes)):
    if s in seen or s not in edges: continue
    st, comp = [s], []
    seen.add(s)
    while st:
        u = st.pop(); comp.append(u)
        for v in edges[u]:
            if v not in seen: seen.add(v); st.append(v)
    comps.append(comp)
main = max(comps, key=len); keep = set(main)
remap = {old: i for i, old in enumerate(sorted(keep))}
N = [nodes[o] for o in sorted(keep)]
E = [[remap[u], remap[v], round(w, 1)] for u in keep for v, w in edges[u].items() if v in keep and u < v]
# node -> road names (for street matching)
names = collections.defaultdict(set)
for rd in R:
    for p in rd["pts"]:
        k = key(p)
        if k in idx and idx[k] in remap and rd["n"]: names[remap[idx[k]]].add(rd["n"])
photos = json.load(open(photos_path))["photos"]
PH = [{"id": p["id"], "x": p["x"], "y": p["y"], "err": p["pos_err_m"], "prov": p["pos_prov"],
       "street": p["street_matched"], "t": p["t_local"]} for p in photos]
commons = list(csv.DictReader(open(commons_path, encoding="utf-8")))
CM = [{"street": r.get("street", ""), "what": r.get("what_it_shows", "")[:80], "quarter": r.get("quarter", "")} for r in commons]
data = {"v": 0, "frame": "twin tile frame (EPSG:2039 + world offset)", "buildings": B,
        "roads": [{"n": r["n"], "pts": r["pts"]} for r in R], "graph": {"nodes": N, "edges": E,
        "names": {str(k): sorted(v) for k, v in names.items()}}, "photos": PH, "commons": CM}
json.dump(data, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
print("buildings", len(B), "roads", len(R), "graph nodes", len(N), "of", len(nodes), "edges", len(E),
      "components", len(comps), "photos", len(PH), "commons", len(CM), "bytes", os.path.getsize(out))
print("src", collections.Counter(b["src"] for b in B).most_common(), "floors", collections.Counter(b["f"] for b in B).most_common(8))

# ---------------- v0 jobs (real, checkable work) + compact output for the viewer ----------------
def near_nodes(x, y, r):
    return [i for i, n in enumerate(N) if (n[0] - x) ** 2 + (n[1] - y) ** 2 <= r * r]
def norm(s): return (s or "").replace("ו", "").replace(" ", "")
jobs = []
for p in PH:
    r = max(p["err"], 15)
    nn = min(range(len(N)), key=lambda i: (N[i][0] - p["x"]) ** 2 + (N[i][1] - p["y"]) ** 2)
    same = [int(i) for i, v in names.items() if p["street"] and any(norm(p["street"]) == norm(s) for s in v)]
    dsame = min((math.dist(N[i], (p["x"], p["y"])) for i in same), default=None)
    variants = sorted({s for i in near_nodes(p["x"], p["y"], r) for s in names.get(i, set()) if norm(s) == norm(p["street"]) and s != p["street"]})
    cand = sorted(((math.dist(b["c"], (p["x"], p["y"])), b) for b in B if math.dist(b["c"], (p["x"], p["y"])) <= r), key=lambda t: t[0])
    verdict = ("no street on record" if not p["street"] else
               "consistent" if dsame is not None and dsame <= r else "inconsistent")
    jobs.append({"kind": "photo", "id": p["id"], "node": nn, "x": p["x"], "y": p["y"], "r": round(r, 1), "street": p["street"],
                 "prov": p["prov"], "d_street": None if dsame is None else round(dsame, 1), "verdict": verdict,
                 "variants": variants, "n_cand": len(cand), "cand": [b["id"] for _, b in cand[:5]],
                 "cand_no_height": sum(1 for _, b in cand if b["src"] == "R")})
street_nodes = collections.defaultdict(list)
for i, v in names.items():
    for s in v: street_nodes[norm(s)].append(int(i))
for k, c in enumerate(CM):
    st = c["street"] or ""
    hits = street_nodes.get(norm(st.replace("רחוב", "").strip()), [])
    if hits:
        mid = hits[len(hits) // 2]
        jobs.append({"kind": "commons", "id": f"C{k+1:02d}", "node": mid, "x": N[mid][0], "y": N[mid][1], "street": st,
                     "what": c["what"], "verdict": "street found", "n_nodes": len(hits)})
    else:
        jobs.append({"kind": "commons", "id": f"C{k+1:02d}", "node": None, "street": st, "what": c["what"], "verdict": "street not in map"})
summ = collections.Counter((j["kind"], j["verdict"]) for j in jobs)
print("jobs", len(jobs), dict(summ))
print("spelling variants seen:", sorted({v for j in jobs for v in j.get("variants", [])}))
cx0 = min(n[0] for n in N); cy0 = min(n[1] for n in N)
compact = {"v": 0, "o": [cx0, cy0],
           "b": [[round(b["c"][0] - cx0), round(b["c"][1] - cy0), b["f"] or 0, 1 if b["src"] == "R" else 0, b["n"],
                  [v for q in b["p"] for v in (round(q[0]), round(q[1]))]] for b in B],
           "n": [[n[0] - cx0, n[1] - cy0] for n in N], "e": [[u, v] for u, v, w in E],
           "jobs": [dict(j, x=None if j.get("x") is None else round(j["x"] - cx0, 1), y=None if j.get("y") is None else round(j["y"] - cy0, 1)) for j in jobs]}
cpath = out.replace(".json", "_compact.json")
json.dump(compact, open(cpath, "w"), ensure_ascii=False, separators=(",", ":"))
json.dump(jobs, open(out.replace(".json", "_jobs.json"), "w"), ensure_ascii=False, indent=1)
print("compact bytes", os.path.getsize(cpath))
