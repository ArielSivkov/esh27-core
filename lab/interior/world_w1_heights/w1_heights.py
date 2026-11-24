"""W1 (Kaggle CPU kernel): open building-height sources for Ashdod. See PREREG.md.
Prints a summary and a compact candidate CSV to stdout (file download is blocked on the lab side)."""
import json, subprocess, sys, time, re, math, collections
import requests
import numpy as np

BBOX = (34.60, 31.74, 34.72, 31.86)  # W,S,E,N
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)

# ---------- 1. OSM via Overpass ----------
q = f"""[out:json][timeout:180];
(way["building"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]}););
out tags geom;"""
osm = None
for url in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]:
    try:
        r = requests.post(url, data={"data": q}, timeout=240)
        if r.ok: osm = r.json()["elements"]; log("overpass ok", url, len(osm)); break
        log("overpass", url, r.status_code)
    except Exception as e:
        log("overpass fail", url, repr(e)[:120])
if osm is None: log("OSM UNAVAILABLE"); osm = []

def num(s):
    if s is None: return None
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(m)?\s*$", str(s))
    return float(m.group(1)) if m else None

from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
O = []
for e in osm:
    g = e.get("geometry")
    if not g or len(g) < 4: continue
    try: poly = Polygon([(p["lon"], p["lat"]) for p in g])
    except Exception: continue
    if not poly.is_valid: poly = poly.buffer(0)
    t = e.get("tags", {})
    O.append({"id": e["id"], "poly": poly, "levels": num(t.get("building:levels")), "height": num(t.get("height")),
              "name": t.get("name:he") or t.get("name") or ""})
# footprint area in m^2 (local equirectangular)
k = 111320.0; kx = k * math.cos(math.radians(31.8))
for o in O: o["area"] = o["poly"].area * k * kx
log("OSM buildings", len(O))

# ---------- 2. Overture ----------
subprocess.run("pip install -q overturemaps", shell=True)
ov_rows = []
try:
    subprocess.run(f"overturemaps download --bbox={BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]} -f geoparquet --type=building -o /tmp/ov.parquet",
                   shell=True, check=True, timeout=1800)
    import geopandas as gpd
    ov = gpd.read_parquet("/tmp/ov.parquet")
    log("overture buildings", len(ov), "cols", list(ov.columns)[:25])
    for _, r in ov.iterrows():
        srcs = r.get("sources")
        srcs = list(srcs) if srcs is not None else []
        osm_rec, h_src, f_src, all_ds = None, None, None, set()
        for s in srcs:
            s = dict(s); ds = s.get("dataset"); prop = s.get("property") or ""; all_ds.add(ds)
            rid = s.get("record_id") or ""
            if ds == "OpenStreetMap" and rid.startswith("w"): osm_rec = int(re.match(r"w(\d+)", rid).group(1))
            if "height" in prop: h_src = ds
            if "num_floors" in prop: f_src = ds
        # whole-feature source applies when no property-level source given
        feat_ds = [dict(s).get("dataset") for s in srcs if not (dict(s).get("property") or "")]
        if h_src is None and len(feat_ds) == 1: h_src = feat_ds[0]
        if f_src is None and len(feat_ds) == 1: f_src = feat_ds[0]
        h = r.get("height"); f = r.get("num_floors")
        ov_rows.append({"geom": r.geometry, "height": float(h) if h is not None and not (isinstance(h, float) and math.isnan(h)) else None,
                        "floors": float(f) if f is not None and not (isinstance(f, float) and math.isnan(f)) else None,
                        "h_src": h_src, "f_src": f_src, "osm": osm_rec, "ds": sorted(x for x in all_ds if x)})
except Exception as e:
    log("OVERTURE UNAVAILABLE", repr(e)[:300])

# ---------- 3. summaries ----------
S = {"bbox": BBOX, "osm_n": len(O), "overture_n": len(ov_rows)}
S["osm_with_levels"] = sum(o["levels"] is not None for o in O)
S["osm_with_height"] = sum(o["height"] is not None for o in O)
S["overture_datasets"] = collections.Counter(d for r in ov_rows for d in r["ds"]).most_common()
S["overture_height_src"] = collections.Counter(r["h_src"] for r in ov_rows if r["height"] is not None).most_common()
S["overture_floors_src"] = collections.Counter(r["f_src"] for r in ov_rows if r["floors"] is not None).most_common()
ind = [r for r in ov_rows if (r["height"] is not None and r["h_src"] not in (None, "OpenStreetMap")) or
       (r["floors"] is not None and r["f_src"] not in (None, "OpenStreetMap"))]
S["overture_independent_values"] = len(ind)
S["overture_height_value_spikes"] = collections.Counter(round(r["height"], 1) for r in ov_rows if r["height"] is not None).most_common(8)
S["osm_levels_spikes"] = collections.Counter(o["levels"] for o in O if o["levels"] is not None).most_common(8)

# ---------- 4. match independent Overture values to OSM ----------
by_id = {o["id"]: o for o in O}
tree = STRtree([o["poly"] for o in O]) if O else None
def osm_floor_est(o):
    if o["levels"] is not None: return o["levels"], "levels"
    if o["height"] is not None: return (o["height"] - 1.0) / 3.0, "height"
    return None, None
pairs, multi = [], 0
for r in ind:
    o = by_id.get(r["osm"]) if r["osm"] else None
    if o is None and tree is not None:
        c = r["geom"].centroid
        hits = [O[i] for i in tree.query(c) if O[i]["poly"].contains(c)]
        if len(hits) > 1: multi += 1; continue
        o = hits[0] if hits else None
    ov_f = r["floors"] if (r["floors"] is not None and r["f_src"] != "OpenStreetMap") else ((r["height"] - 1.0) / 3.0)
    ov_srcname = r["f_src"] if (r["floors"] is not None and r["f_src"] != "OpenStreetMap") else r["h_src"]
    if o is None:
        pairs.append({"osm": None, "osm_f": None, "ov_f": ov_f, "ov_src": ov_srcname, "area": None, "name": ""}); continue
    of, how = osm_floor_est(o)
    pairs.append({"osm": o["id"], "osm_f": of, "osm_how": how, "ov_f": ov_f, "ov_src": ov_srcname, "area": o["area"], "name": o["name"]})
S["independent_matched_to_osm_building"] = sum(p["osm"] is not None for p in pairs)
S["independent_multi_match_excluded"] = multi
both = [p for p in pairs if p["osm_f"] is not None]
S["both_sources_n"] = len(both)
if both:
    d = np.array([abs(p["osm_f"] - p["ov_f"]) for p in both])
    S["both_within_1_floor_share"] = float((d <= 1).mean())
    S["both_median_abs_diff_floors"] = float(np.median(d))
cands = [p for p in both if abs(p["osm_f"] - p["ov_f"]) <= 1]
S["TASK7_CANDIDATES_n2_within1"] = len(cands)
# coverage by footprint area bin
bins = [0, 100, 300, 1000, 3000, 1e9]
cov = {}
for lo, hi in zip(bins[:-1], bins[1:]):
    sel = [o for o in O if lo <= o["area"] < hi]
    ids = {p["osm"] for p in pairs if p["osm"] is not None}
    cov[f"{int(lo)}-{int(hi) if hi < 1e9 else 'inf'}m2"] = {"n": len(sel), "osm_levels": sum(o["levels"] is not None for o in sel),
                                                         "indep_overture": sum(o["id"] in ids for o in sel)}
S["coverage_by_area"] = cov
for wid in (1280878706, 1013192689):
    o = by_id.get(wid)
    S[f"anchor_w{wid}"] = None if o is None else {"levels": o["levels"], "height": o["height"], "name": o["name"],
                                                   "overture": [p for p in pairs if p["osm"] == wid]}
print("=====SUMMARY=====")
print(json.dumps(S, ensure_ascii=False, default=str, indent=1))
print("=====CANDIDATES_CSV=====")
print("osm_way,osm_floors,osm_how,ov_floors,ov_src,area_m2,name")
for p in sorted(cands, key=lambda p: -(p["area"] or 0)):
    print(f'{p["osm"]},{p["osm_f"]:.1f},{p["osm_how"]},{p["ov_f"]:.1f},{p["ov_src"]},{p["area"]:.0f},"{p["name"]}"')
print("=====DISAGREE_CSV (top 60 by area)=====")
dis = [p for p in both if abs(p["osm_f"] - p["ov_f"]) > 1]
for p in sorted(dis, key=lambda p: -(p["area"] or 0))[:60]:
    print(f'{p["osm"]},{p["osm_f"]:.1f},{p["osm_how"]},{p["ov_f"]:.1f},{p["ov_src"]},{p["area"]:.0f},"{p["name"]}"')
print("=====INDEPENDENT_ONLY (no OSM value), top 80 by floors=====")
only = [p for p in pairs if p["osm_f"] is None]
for p in sorted(only, key=lambda p: -p["ov_f"])[:80]:
    print(f'{p["osm"]},{p["ov_f"]:.1f},{p["ov_src"]},{p["area"] if p["area"] is None else round(p["area"])},"{p["name"]}"')
log("DONE")
