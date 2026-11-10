"""Harvester for the public Sefaria export (storage.googleapis.com/sefaria-export).

Every file is downloaded, hashed and passed through the legal gate. Only
versions whose own `license` field is allowed by bhm.legal are stored.
"merged.json" files are skipped: they mix versions with different licenses.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import sys
import urllib.parse
import urllib.request

from . import library

BUCKET = "https://storage.googleapis.com/sefaria-export"
LIST_API = "https://storage.googleapis.com/storage/v1/b/sefaria-export/o"


def list_files(prefix: str = "json/") -> list[dict]:
    items, tok = [], None
    while True:
        q = {"prefix": prefix, "fields": "items(name,size),nextPageToken", "maxResults": "1000"}
        if tok:
            q["pageToken"] = tok
        with urllib.request.urlopen(f"{LIST_API}?{urllib.parse.urlencode(q)}", timeout=60) as r:
            d = json.load(r)
        items += d.get("items", [])
        tok = d.get("nextPageToken")
        if not tok:
            return items


def wanted(name: str, languages=("Hebrew",)) -> bool:
    parts = name.split("/")
    return name.endswith(".json") and not name.endswith("/merged.json") and any(f"/{l}/" in name for l in languages) and len(parts) > 3


def fetch(name: str, retries: int = 4) -> bytes:
    url = f"{BUCKET}/{urllib.parse.quote(name)}"
    last = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception as e:  # network hiccup: retry
            last = e
    raise last


def harvest(con, prefix: str = "json/", allow_tier_b: bool = True, workers: int = 12, log=print) -> dict:
    done = {r["origin"] for r in con.execute("SELECT origin FROM versions")}
    seen = {r["origin"] for r in con.execute("SELECT DISTINCT origin FROM legal_log")}
    files = [f for f in list_files(prefix) if wanted(f["name"])]
    todo = [f for f in files if f"sefaria:{f['name']}" not in done | seen]
    log(f"{len(files)} files under {prefix}; {len(todo)} to process")
    stats = {"imported": 0, "rejected": 0, "errors": 0, "segments": 0}
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch, f["name"]): f for f in todo}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            f = futs[fut]
            origin = f"sefaria:{f['name']}"
            try:
                raw = fut.result()
                meta = json.loads(raw)
                ok, dec, n = library.import_version(con, meta, origin, hashlib.sha256(raw).hexdigest(), allow_tier_b)
                stats["imported" if ok else "rejected"] += 1
                stats["segments"] += n
            except Exception as e:
                stats["errors"] += 1
                log(f"error {f['name']}: {e}")
            if i % 250 == 0:
                log(f"{i}/{len(todo)} {stats}")
                sys.stdout.flush()
    return stats
