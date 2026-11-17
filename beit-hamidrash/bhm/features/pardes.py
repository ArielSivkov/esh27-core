"""פרדס רימונים: 32 שערים, קישור לקריאה בספרייה ולאתר הלימוד הסטטי (ל"ב דרכים)."""
from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

NAV = {"label": "פרדס רימונים", "href": "#/pardes"}
TITLE = "Pardes Rimmonim"
SITE = Path(__file__).resolve().parents[3] / "pardes"
REF = re.compile(r"^" + re.escape(TITLE) + r" (\d+):(\d+):1$")
ALLOWED = {".html", ".js", ".css", ".json", ".txt", ".svg", ".png", ".ico", ".woff2"}
MEDIA = {".json": "application/json", ".js": "text/javascript", ".css": "text/css", ".html": "text/html"}


def _meta() -> list[dict]:
    try:
        return json.loads((SITE / "data" / "meta.json").read_text("utf-8"))["gates"]
    except (OSError, ValueError, KeyError):
        return []


def _refs(con) -> dict[int, list[str]]:
    """gate -> ordered chapter refs (first paragraph of each chapter, so #/goto lands in that chapter).
    Uses the first version of the book that has refs of the form 'Pardes Rimmonim G:C:P'."""
    out: dict[int, list[str]] = {}
    for v in con.execute("SELECT id FROM versions WHERE title=? ORDER BY id", (TITLE,)).fetchall():
        rows = con.execute("SELECT ref FROM segments WHERE version_id=? AND ref LIKE ? ORDER BY seq",
                           (v["id"], TITLE + " %:%:1")).fetchall()
        for r in rows:
            m = REF.match(r["ref"])
            if m:
                out.setdefault(int(m.group(1)), []).append(r["ref"])
        if out:
            break
    return out


def safe_path(rel: str) -> Path | None:
    """Resolve rel inside SITE; None if outside, missing, not a file, hidden or disallowed type."""
    if "\x00" in rel or "\\" in rel:
        return None
    base = SITE.resolve()
    try:
        p = (base / rel).resolve()
        parts = p.relative_to(base).parts
    except (ValueError, OSError):
        return None
    if not p.is_file() or p.suffix.lower() not in ALLOWED:
        return None
    if any(part.startswith(".") for part in parts):
        return None
    return p


def make_router(node) -> APIRouter:
    r = APIRouter(prefix="/api/pardes")

    @r.get("/gates")
    def gates():
        refs = _refs(node.con)
        out = []
        for g in _meta():
            n = g["n"]
            out.append({"n": n, "heb": g.get("heb"), "title": g.get("title"), "chapters": g.get("chapters"),
                        "refs": refs.get(n, []), "way": f"#/way/{n}",
                        "site": "/api/pardes/site/index.html"})
        return {"title": TITLE, "he_title": "פרדס רמונים", "gates": out,
                "note": "הקישורים לקריאה מובילים לטקסט הספרייה; האתר הסטטי הוא כלי עזר ללימוד, לא פסק הלכה."}

    @r.get("/site")
    @r.get("/site/")
    def site_root():
        return site_file("index.html")

    @r.get("/site/{path:path}")
    def site_file(path: str):
        p = safe_path(path or "index.html")
        if p is None:
            raise HTTPException(404, "לא נמצא")
        mt = MEDIA.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return FileResponse(p, media_type=mt, headers={"X-Content-Type-Options": "nosniff"})

    return r
