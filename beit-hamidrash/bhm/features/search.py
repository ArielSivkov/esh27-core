"""Full-text search over library segments (SQLite FTS5, Hebrew-normalized).

Index: search_fts(ref, version_id UNINDEXED, text) where text is normalized (no nikud/te'amim,
maqaf -> space, punctuation removed). rowid of an index row == rowid of its segment.
Build:  python3 -m bhm.features.search build [--rebuild]
If the index is missing the API falls back to a (slow) LIKE scan over normalized text.
"""
from __future__ import annotations

import re
import sys

from fastapi import APIRouter, Query

NAV = {"label": "חיפוש", "href": "#/search"}

HL_OPEN, HL_CLOSE = "⟦", "⟧"   # highlight markers; the web client escapes, then turns them into <mark>
_STRIP = re.compile("[֑-ׇ]")
_NONWORD = re.compile(r"[^\wא-ת]+")


def norm(s: str | None) -> str:
    """Hebrew normalization: nikud/te'amim removed (maqaf becomes a space), punctuation dropped, lowercase."""
    if not s:
        return ""
    s = s.replace("־", " ")
    s = _STRIP.sub("", s)
    return _NONWORD.sub(" ", s).lower().strip()


def _norm_map(s: str) -> tuple[str, list[int]]:
    """Normalize while keeping, for each output char, its index in the original (for highlighting)."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch == "־":
            out.append(" ")
        elif "֑" <= ch <= "ׇ":
            continue
        elif ch.isalnum() or ch == "_" or "א" <= ch <= "ת":
            out.append(ch.lower())
        else:
            out.append(" ")
        idx.append(i)
    return "".join(out), idx


def has_index(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE name='search_fts'").fetchone() is not None


def build_index(con, rebuild: bool = False, batch: int = 20000) -> int:
    """Create/refresh the index. Incremental: only segments newer than the highest indexed rowid. Returns rows added."""
    con.create_function("bhm_norm", 1, norm)
    if rebuild:
        con.execute("DROP TABLE IF EXISTS search_fts")
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(ref, version_id UNINDEXED, text, "
                "tokenize='unicode61 remove_diacritics 0')")
    last = con.execute("SELECT COALESCE(MAX(rowid),0) FROM search_fts").fetchone()[0]
    top = con.execute("SELECT COALESCE(MAX(rowid),0) FROM segments").fetchone()[0]
    added = 0
    while last < top:
        cur = con.execute("INSERT INTO search_fts(rowid, ref, version_id, text) "
                          "SELECT rowid, ref, version_id, bhm_norm(text) FROM segments WHERE rowid>? AND rowid<=?",
                          (last, last + batch))
        added += cur.rowcount
        last += batch
        con.commit()
    con.commit()
    return added


def _fts_query(q: str) -> str | None:
    toks = norm(q).split()
    return " ".join(f'"{t}"*' for t in toks[:12]) if toks else None


def make_snippet(text: str, terms: list[str], width: int = 80) -> str:
    """Window of the ORIGINAL text around the first hit, hits wrapped in HL markers."""
    n, idx = _norm_map(text)
    spans = []
    for t in terms:
        for m in re.finditer(r"(?<![\wא-ת])" + re.escape(t), n):
            spans.append((idx[m.start()], idx[m.end() - 1] + 1))
    if not spans:
        return text[:width * 2]
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    start = max(0, merged[0][0] - width)
    end = min(len(text), merged[0][0] + width * 2)
    out, pos = [], start
    for a, b in merged:
        if b <= start or a >= end:
            continue
        a, b = max(a, start), min(b, end)
        out += [text[pos:a], HL_OPEN, text[a:b], HL_CLOSE]
        pos = b
    out.append(text[pos:end])
    return ("…" if start else "") + "".join(out) + ("…" if end < len(text) else "")


def search(con, q: str, book: str = "", category: str = "", limit: int = 20, offset: int = 0) -> dict:
    con.create_function("bhm_norm", 1, norm)
    terms = norm(q).split()
    if not terms:
        return {"mode": "none", "results": [], "count": 0}
    where, args = [], []
    if book:
        where.append("v.title=?"); args.append(book)
    if category:
        where.append("json_extract(v.categories,'$[0]')=?"); args.append(category)
    extra = (" AND " + " AND ".join(where)) if where else ""
    if has_index(con):
        mode = "fts"
        sql = ("SELECT s.ref, s.text, v.title, v.he_title, v.version_title FROM search_fts f "
               "JOIN segments s ON s.rowid=f.rowid JOIN versions v ON v.id=s.version_id "
               f"WHERE search_fts MATCH ?{extra} ORDER BY f.rank LIMIT ? OFFSET ?")
        params = [_fts_query(q)] + args + [limit, offset]
    else:
        mode = "like"
        cond = " AND ".join("bhm_norm(s.text) LIKE ?" for _ in terms)
        sql = ("SELECT s.ref, s.text, v.title, v.he_title, v.version_title FROM segments s "
               f"JOIN versions v ON v.id=s.version_id WHERE {cond}{extra} ORDER BY s.rowid LIMIT ? OFFSET ?")
        params = [f"%{t}%" for t in terms] + args + [limit, offset]
    rows = con.execute(sql, params).fetchall()
    res = [{"ref": r["ref"], "book": r["title"], "he_book": r["he_title"], "version_title": r["version_title"],
            "snippet": make_snippet(r["text"], terms)} for r in rows]
    return {"mode": mode, "results": res, "count": len(res), "offset": offset, "markers": [HL_OPEN, HL_CLOSE]}


def make_router(node) -> APIRouter:
    r = APIRouter()

    @r.get("/api/search/q")
    def q_(q: str = "", book: str = "", category: str = "", limit: int = Query(20, ge=1, le=100),
           offset: int = Query(0, ge=0)):
        return search(node.con, q.strip()[:200], book, category, limit, offset)

    @r.get("/api/search/status")
    def status():
        con = node.con
        if not has_index(con):
            return {"indexed": False}
        n = con.execute("SELECT COUNT(*) FROM search_fts").fetchone()[0]
        total = con.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
        return {"indexed": True, "rows": n, "segments": total, "stale": n < total}

    @r.get("/api/search/categories")
    def cats():
        return [x[0] for x in node.con.execute(
            "SELECT DISTINCT json_extract(categories,'$[0]') FROM versions ORDER BY 1") if x[0]]

    return r


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        from bhm.node import Node
        n = Node()
        print("indexed", build_index(n.con, rebuild="--rebuild" in sys.argv), "segments")
    else:
        print("usage: python3 -m bhm.features.search build [--rebuild]")
