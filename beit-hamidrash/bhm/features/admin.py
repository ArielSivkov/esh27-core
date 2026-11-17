"""Admin feature: read-only node dashboard. GET /api/admin/stats (counts cached in-process, 60s TTL)."""
from __future__ import annotations

import re
import threading
import time

from fastapi import APIRouter, HTTPException, Request

from .. import ledger

NAV = {"label": "ניהול", "href": "#/admin"}
TTL = 60.0
_REF_BOOK = re.compile(r"[\s\d:.,\-–]+$")
_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def _book_of(ref: str) -> str:
    """'Genesis 1:1' -> 'Genesis'."""
    return _REF_BOOK.sub("", ref or "").strip() or (ref or "")


def compute(node) -> dict:
    con = node.con
    one = lambda q: con.execute(q).fetchone()[0]
    tiers = {r["tier"]: r["n"] for r in con.execute("SELECT tier, COUNT(*) n FROM versions GROUP BY tier")}
    kinds = {r["kind"]: r["n"] for r in con.execute("SELECT kind, COUNT(*) n FROM events GROUP BY kind")}
    per_book: dict[str, int] = {}
    for r in con.execute("SELECT ref, COUNT(*) n FROM events WHERE kind='commentary' AND ref IS NOT NULL GROUP BY ref"):
        b = _book_of(r["ref"])
        per_book[b] = per_book.get(b, 0) + r["n"]
    top = sorted(per_book.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    he = {}
    for b, _ in top:
        row = con.execute("SELECT he_title FROM versions WHERE title=? AND he_title IS NOT NULL LIMIT 1", (b,)).fetchone()
        he[b] = row[0] if row else ""
    db = node.home / "library.db"
    size = sum(p.stat().st_size for p in (db, db.with_name("library.db-wal")) if p.exists())
    return {
        "versions_by_tier": tiers,
        "versions": sum(tiers.values()),
        "segments": one("SELECT COUNT(*) FROM segments"),
        "books": one("SELECT COUNT(DISTINCT title) FROM versions"),
        "events_by_kind": kinds,
        "events": sum(kinds.values()),
        "authors": one("SELECT COUNT(DISTINCT author) FROM events"),
        "hidden": len(ledger.hidden(con)),
        "trusted_authorities": [{"name": r["name"], "fingerprint": r["pubkey"][:16], "added_at": r["added_at"]}
                                for r in con.execute("SELECT pubkey, name, added_at FROM trusted_authorities ORDER BY added_at")],
        "imported_bundles": [dict(r) for r in con.execute(
            "SELECT id, authority, created, imported_at, events, versions FROM imported_bundles ORDER BY imported_at DESC LIMIT 50")],
        "imported_bundles_count": one("SELECT COUNT(*) FROM imported_bundles"),
        "legal_log": {r["decision"]: r["n"] for r in con.execute("SELECT decision, COUNT(*) n FROM legal_log GROUP BY decision")},
        "db_size_bytes": size,
        "top_books_by_commentary": [{"book": b, "he_title": he.get(b) or "", "count": n} for b, n in top],
    }


def make_router(node) -> APIRouter:
    r = APIRouter(prefix="/api/admin")

    @r.get("/stats")
    def stats(request: Request, refresh: bool = False):
        if request.client is None or request.client.host not in ("127.0.0.1", "::1", "testclient"):
            raise HTTPException(403, "local requests only")
        key = str(node.home)
        now = time.monotonic()
        with _lock:
            hit = _cache.get(key)
            if hit and not refresh and now - hit[0] < TTL:
                return {**hit[1], "cached": True, "ttl": TTL}
        data = compute(node)
        data["generated_at"] = ledger.now()
        with _lock:
            _cache[key] = (time.monotonic(), data)
        return {**data, "cached": False, "ttl": TTL}

    return r
