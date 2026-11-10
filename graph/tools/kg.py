#!/usr/bin/env python3
"""ESH27 knowledge graph: validate / metrics / verify.

  python3 graph/tools/kg.py validate   # structure rules, no network
  python3 graph/tools/kg.py metrics    # counts, Betti numbers, PageRank, betweenness
  python3 graph/tools/kg.py verify     # check every quote against the Sefaria API
"""
import json, re, sys, unicodedata, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODE_TYPES = {"person", "work", "concept", "sefira", "school", "place", "event"}
EDGE_TYPES = {
    "E1": "מסירה רב-תלמיד", "E2": "שושלת משפחתית", "E3": "מחלוקת / בר פלוגתא",
    "E4": "פירוש / קודיפיקציה על חיבור", "E5": "ארכיטיפ / שורש", "E6": "קרבה מתודולוגית מחושבת",
    "AUTHORED": "חיבר", "CHANNEL": "צינור בין ספירות", "MAPS_TO": "מיפוי בין שכבות",
}
SYMMETRIC = {"E3", "E6"}
BASIS = {"EXTRACTED", "INFERRED", "STRUCTURAL_MAPPING"}
MUST_BE_SOURCED = {"E1", "E2", "E3", "E4", "AUTHORED"}   # historical / textual claims
MUST_BE_MAPPING = {"E5", "E6", "CHANNEL", "MAPS_TO"}     # analogy, never stated as fact
RANKS = {"preferred", "normal", "deprecated"}
ID_RE = re.compile(r"^[a-z]+:[a-z0-9_\-]+$")


def load():
    nodes = json.loads((ROOT / "data/nodes.json").read_text(encoding="utf-8"))
    edges = json.loads((ROOT / "data/edges.json").read_text(encoding="utf-8"))
    return nodes, edges


def validate(nodes, edges):
    errs, ids, eids = [], set(), set()
    for n in nodes:
        i = n.get("id", "")
        if not ID_RE.match(i): errs.append(f"node id לא תקין: {i!r}")
        if i in ids: errs.append(f"node כפול: {i}")
        ids.add(i)
        if n.get("type") not in NODE_TYPES: errs.append(f"{i}: type לא מוכר")
        if i.split(":")[0] != n.get("type"): errs.append(f"{i}: קידומת המזהה שונה מה-type")
        for f in ("label_he", "layer", "text_he"):
            if not n.get(f): errs.append(f"{i}: חסר {f}")
    for e in edges:
        i = e.get("id", "?")
        if i in eids: errs.append(f"edge כפול: {i}")
        eids.add(i)
        for end in ("source", "target", "claimed_by"):
            v = e.get(end)
            if v is None and end == "claimed_by": continue
            if v not in ids: errs.append(f"{i}: {end} לא קיים: {v}")
        if e.get("source") == e.get("target"): errs.append(f"{i}: לולאה עצמית")
        t, b = e.get("type"), e.get("basis")
        if t not in EDGE_TYPES: errs.append(f"{i}: type לא מוכר: {t}")
        if b not in BASIS: errs.append(f"{i}: basis לא מוכר: {b}")
        if e.get("rank") not in RANKS: errs.append(f"{i}: rank לא מוכר")
        if t in MUST_BE_MAPPING and b != "STRUCTURAL_MAPPING":
            errs.append(f"{i}: קשת {t} חייבת basis=STRUCTURAL_MAPPING")
        if t in MUST_BE_SOURCED:
            if b == "STRUCTURAL_MAPPING": errs.append(f"{i}: קשת {t} אינה משל")
            good = [r for r in e.get("refs", []) if r.get("sefaria_ref") and len(r.get("quote", "").split()) >= 3]
            if b == "EXTRACTED" and not good:
                errs.append(f"{i}: EXTRACTED דורש מראה מקום וציטוט של 3 מילים לפחות")
    for e in edges:
        for d in e.get("disputes", []):
            if d not in eids: errs.append(f"{e['id']}: disputes מצביע על קשת חסרה {d}")
    return errs


def metrics(nodes, edges):
    import networkx as nx
    live = [e for e in edges if e.get("rank") != "deprecated"]
    g = nx.Graph()
    g.add_nodes_from(n["id"] for n in nodes)
    g.add_edges_from((e["source"], e["target"]) for e in live)
    b0 = nx.number_connected_components(g)
    out = {
        "nodes": g.number_of_nodes(), "claims": len(live), "undirected_edges": g.number_of_edges(),
        "betti_0": b0, "betti_1": g.number_of_edges() - g.number_of_nodes() + b0,
        "by_type": {}, "by_basis": {},
    }
    for e in live:
        out["by_type"][e["type"]] = out["by_type"].get(e["type"], 0) + 1
        out["by_basis"][e["basis"]] = out["by_basis"].get(e["basis"], 0) + 1
    dg = nx.DiGraph()
    dg.add_nodes_from(g.nodes)
    for e in live:
        dg.add_edge(e["source"], e["target"])
        if e["type"] in SYMMETRIC: dg.add_edge(e["target"], e["source"])
    pr, bc = pagerank(dg), nx.betweenness_centrality(g)
    top = lambda d: [[k, round(v, 4)] for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:10]]
    out["pagerank_top"], out["betweenness_top"] = top(pr), top(bc)
    return out


def pagerank(dg, alpha=0.85, iters=200):
    """Plain power iteration, so the numbers need nothing beyond networkx."""
    ns = sorted(dg.nodes)
    pr = {n: 1 / len(ns) for n in ns}
    for _ in range(iters):
        dangling = sum(pr[n] for n in ns if dg.out_degree(n) == 0)
        pr = {n: (1 - alpha) / len(ns) + alpha * (dangling / len(ns) +
              sum(pr[m] / dg.out_degree(m) for m in dg.predecessors(n))) for n in ns}
    return pr


def norm(s):
    """Strip HTML, nikud and cantillation, unify maqaf/punctuation, plene vs defective spelling."""
    s = re.sub(r"<[^>]+>", " ", s).replace("־", " ")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^א-ת ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def loose(s):
    return re.sub(r"[וי]", "", norm(s))  # ignores ktiv male/haser differences


def flat(x):
    return x if isinstance(x, str) else " ".join(flat(i) for i in x)


def verify(edges):
    cache, bad, n = {}, [], 0
    for e in edges:
        for r in e.get("refs", []):
            ref, n = r["sefaria_ref"], n + 1
            if ref not in cache:
                url = f"https://www.sefaria.org/api/texts/{ref}?context=0&commentary=0"
                try:
                    with urllib.request.urlopen(url, timeout=30) as f:
                        cache[ref] = flat(json.load(f).get("he", ""))
                except Exception as ex:
                    cache[ref] = None
                    bad.append(f"{e['id']}: לא נמשך {ref} ({ex})")
            text = cache[ref]
            if text is not None and loose(r["quote"]) not in loose(text):
                bad.append(f"{e['id']}: הציטוט לא נמצא ב-{ref}: {r['quote']}")
    return n, bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "validate"
    nodes, edges = load()
    errs = validate(nodes, edges)
    if errs:
        print("\n".join(errs)); sys.exit(1)
    if cmd == "validate":
        print(f"תקין: {len(nodes)} צמתים, {len(edges)} קשתות")
    elif cmd == "metrics":
        print(json.dumps(metrics(nodes, edges), ensure_ascii=False, indent=2))
    elif cmd == "verify":
        n, bad = verify(edges)
        print("\n".join(bad) if bad else f"אומתו {n} ציטוטים מול ספריא")
        sys.exit(1 if bad else 0)
    else:
        print(__doc__); sys.exit(2)
