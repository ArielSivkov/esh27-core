#!/usr/bin/env python3
"""Rebuild the large raw inputs of the topology work from public Hugging Face mirrors.

  build_data.py arxiv2021    topo/arxiv_all_cats.json   from gfissore/arxiv-abstracts-2021 (pinned revision)
  build_data.py arxiv2026    topo/arxiv_2026_cats.json  from librarian-bots/arxiv-metadata-snapshot (revision recorded)
  build_data.py openalex     topo/oac_counts_s40_t0.4.json via topo/oa_concepts.py, compared with the committed file

Status: written 24.11.2026 in a session where huggingface.co was blocked by the network proxy (HTTP 403),
so this file has NOT been run yet. It is gated: it refuses to start when the host is blocked, and its output
counts only after `verify.py --data` passes (paper counts from the research log, and ipf.py on the rebuilt
2021 data must reproduce the committed topo/ipf_out.json triangle by triangle).

Plain HTTPS against the long-stable /resolve/ and /api/ endpoints is used on purpose, so no client library
version can change the result. Each build writes <output>.meta.json with source, revision, lines and sha256.
"""
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
TOPO = os.path.join(LAB, "topo")
CACHE = os.path.join(LAB, "data", "cache")
HF = "https://huggingface.co"
UA = {"User-Agent": "esh27-lab-rebuild/1"}
CAT_RE = re.compile(r"[A-Za-z\-]+(?:\.[A-Za-z\-]+)?")  # same parser as topo/verify.py, which reproduced the log exactly


def reachable():
    sys.path.insert(0, HERE)
    import hosts
    r = hosts.probe("huggingface.co", HF + "/api/datasets/gfissore/arxiv-abstracts-2021", 15)
    if r["state"] != "reachable":
        raise SystemExit(f"build_data: huggingface.co is {r['state']} from this machine; nothing built, nothing invented")


def download(url, dest):
    if os.path.exists(dest):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 22)
    os.replace(tmp, dest)
    return dest


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def cats_of(value):
    if isinstance(value, list):
        value = " ".join(map(str, value))
    return sorted(set(CAT_RE.findall(value or "")))


def save(out, d, meta):
    with open(out + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(out + ".tmp", out)
    meta.update(output=os.path.relpath(out, LAB), unique_ids=len(d), output_sha256=sha256_file(out),
                built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    json.dump(meta, open(out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta, indent=1))


def arxiv2021():
    repo, rev, name = "gfissore/arxiv-abstracts-2021", "e4c5fbd4dec8e46a5dc869216fe1c94cc585757a", "arxiv-abstracts.jsonl.gz"
    src = download(f"{HF}/datasets/{repo}/resolve/{rev}/{name}", os.path.join(CACHE, repo.replace("/", "__"), rev, name))
    d, lines = {}, 0
    for line in gzip.open(src, "rt"):
        r = json.loads(line)
        lines += 1
        d[r["id"]] = cats_of(r.get("categories"))
    save(os.path.join(TOPO, "arxiv_all_cats.json"), d,
         dict(source=f"hf:{repo}@{rev}/{name}", source_sha256=sha256_file(src), lines=lines))


def arxiv2026():
    repo = "librarian-bots/arxiv-metadata-snapshot"
    info = json.load(urllib.request.urlopen(urllib.request.Request(f"{HF}/api/datasets/{repo}", headers=UA), timeout=60))
    rev, files = info["sha"], [s["rfilename"] for s in info.get("siblings", [])]
    parquet = sorted(f for f in files if f.endswith(".parquet"))
    rows = sorted(f for f in files if re.search(r"\.jsonl?(\.gz)?$", f))
    if not parquet and not rows:
        raise SystemExit(f"build_data: no parquet or json files in {repo}@{rev}: {files[:10]}")
    d, lines, used = {}, 0, []
    for f in (parquet or rows):
        path = download(f"{HF}/datasets/{repo}/resolve/{rev}/{f}", os.path.join(CACHE, repo.replace("/", "__"), rev, f))
        used.append(dict(file=f, sha256=sha256_file(path)))
        if f.endswith(".parquet"):
            import pyarrow.parquet as pq
            t = pq.read_table(path, columns=["id", "categories"]).to_pydict()
            for pid, c in zip(t["id"], t["categories"]):
                d[pid] = cats_of(c)
                lines += 1
        else:
            opener = gzip.open if f.endswith(".gz") else open
            for line in opener(path, "rt"):
                r = json.loads(line)
                d[r["id"]] = cats_of(r.get("categories"))
                lines += 1
    save(os.path.join(TOPO, "arxiv_2026_cats.json"), d,
         dict(source=f"hf:{repo}@{rev}", last_modified=info.get("lastModified"), files=used, lines=lines,
              note="the log's 3,224,542 / 2610.31672 refer to the snapshot of 27.10.2026; a newer snapshot differs"))


def openalex():
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(os.path.join(TOPO, "oa_concepts.py"), t)
        p = subprocess.run([sys.executable, "oa_concepts.py", "40", "0.4"], cwd=t, text=True)
        if p.returncode != 0:
            raise SystemExit("build_data: oa_concepts.py failed")
        new, old = os.path.join(t, "oac_counts_s40_t0.4.json"), os.path.join(TOPO, "oac_counts_s40_t0.4.json")
        same = json.load(open(new)) == json.load(open(old))
        print(f"build_data: OpenAlex concept counts rebuilt; identical to the committed file: {same}")
        if not same:
            shutil.copy(new, os.path.join(LAB, "data", "oac_counts_s40_t0.4.rebuilt.json"))
            raise SystemExit("build_data: rebuilt counts differ from the committed file (kept under data/ for inspection)")


if __name__ == "__main__":
    jobs = dict(arxiv2021=arxiv2021, arxiv2026=arxiv2026, openalex=openalex)
    if len(sys.argv) != 2 or sys.argv[1] not in jobs:
        raise SystemExit(__doc__)
    reachable()
    jobs[sys.argv[1]]()
