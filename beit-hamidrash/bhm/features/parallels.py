"""Mikraot-Gedolot style parallels: commentaries ("<X> on <Book>") around a base verse."""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

NAV = {"label": "מקראות גדולות", "href": "#/parallels/Genesis%201%3A1"}

_REF = re.compile(r"^(.*\S)\s+(\d+[ab]?):(\d+)$")
_CH = re.compile(r"^(.*\S)\s+(\d+[ab]?)$")


def _prefix_range(prefix: str) -> tuple[str, str]:
    return prefix, prefix + "\U0010ffff"


def _commentary_versions(con, book: str) -> list:
    like = "% on " + book.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = con.execute("SELECT id,title,he_title,version_title,language,license,tier FROM versions "
                       "WHERE title LIKE ? ESCAPE '\\' ORDER BY title, tier, version_title", (like,))
    # LIKE is case-insensitive: keep exact-suffix matches only
    return [r for r in rows if r["title"].endswith(" on " + book)]


def make_router(node) -> APIRouter:
    r = APIRouter()

    @r.get("/api/parallels")
    def parallels(ref: str):
        m = _REF.match(ref.strip())
        if not m:
            raise HTTPException(400, "ref must look like 'Genesis 1:1'")
        book, ch, vs = m.group(1), m.group(2), m.group(3)
        base = f"{book} {ch}:{vs}"
        c = node.con
        text = None
        for v in c.execute("SELECT id,version_title,license,language FROM versions WHERE title=? "
                           "ORDER BY (language!='he'), tier, version_title", (book,)).fetchall():
            s = c.execute("SELECT text FROM segments WHERE version_id=? AND ref=? ORDER BY seq LIMIT 1",
                          (v["id"], base)).fetchone()
            if s:
                text = {"ref": base, "version_title": v["version_title"], "license": v["license"],
                        "language": v["language"], "text": s["text"]}
                break
        groups = []
        for v in _commentary_versions(c, book):
            lo, hi = _prefix_range(f"{v['title']} {ch}:{vs}:")
            segs = [{"ref": s["ref"], "text": s["text"]} for s in c.execute(
                "SELECT ref,text FROM segments WHERE version_id=? AND ref>=? AND ref<? ORDER BY seq",
                (v["id"], lo, hi))]
            if segs:
                groups.append({"title": v["title"], "he_title": v["he_title"], "version_title": v["version_title"],
                               "language": v["language"], "license": v["license"], "segments": segs})
        return {"ref": base, "book": book, "base": text, "commentaries": groups}

    @r.get("/api/parallels/count")
    def count(chapter: str):
        m = _CH.match(chapter.strip())
        if not m:
            raise HTTPException(400, "chapter must look like 'Genesis 1'")
        book, ch = m.group(1), m.group(2)
        c = node.con
        counts: dict[str, int] = {}
        titles: dict[str, set] = {}
        for v in _commentary_versions(c, book):
            lo, hi = _prefix_range(f"{v['title']} {ch}:")
            for s in c.execute("SELECT ref FROM segments WHERE version_id=? AND ref>=? AND ref<?",
                               (v["id"], lo, hi)):
                parts = s["ref"][len(v["title"]) + 1:].split(":")
                if len(parts) < 2:
                    continue
                counts[parts[1]] = counts.get(parts[1], 0) + 1
                titles.setdefault(parts[1], set()).add(v["title"])
        order = sorted(counts, key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0, k))
        return {"chapter": f"{book} {ch}", "counts": {k: counts[k] for k in order},
                "commentators": {k: len(titles[k]) for k in order}}

    return r
