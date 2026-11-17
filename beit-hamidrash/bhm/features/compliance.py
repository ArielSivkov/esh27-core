"""Compliance pages (privacy, terms, ...). All are DRAFTS pending lawyer review."""
from __future__ import annotations

import html
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

NAV = {"label": "מדיניות", "href": "#/policies"}
DATA = Path(__file__).resolve().parent / "compliance_data"
ORDER = ["privacy", "terms", "contributor-license", "takedown", "accessibility", "kosher-filter", "shabbat"]
SLUG_RE = re.compile(r"^[a-z0-9-]+$")
DISCLAIMER = "טיוטה לבדיקת עורך דין"


def md_to_html(md: str) -> str:
    """Tiny markdown converter. Everything is HTML-escaped first, then markup is added."""
    out, para, in_ul = [], [], False

    def inline(s: str) -> str:
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    for raw in md.splitlines():
        line = html.escape(raw.rstrip(), quote=True)
        if line.startswith("- "):
            flush()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>" + inline(line[2:]) + "</li>")
            continue
        if in_ul:
            out.append("</ul>")
            in_ul = False
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif line.startswith("&gt; "):
            flush()
            out.append("<blockquote>" + inline(line[5:]) + "</blockquote>")
        elif not line.strip():
            flush()
        else:
            para.append(line)
    flush()
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def _title(md: str, slug: str) -> str:
    for l in md.splitlines():
        if l.startswith("# "):
            return l[2:].strip()
    return slug


def _slugs() -> list[str]:
    have = {p.stem for p in DATA.glob("*.md")}
    return [s for s in ORDER if s in have] + sorted(have - set(ORDER))


def make_router(node) -> APIRouter:
    r = APIRouter(prefix="/api/compliance")

    # own table (convention: compliance_*): counts how often each page was served
    node.con.execute("CREATE TABLE IF NOT EXISTS compliance_views(slug TEXT PRIMARY KEY, n INTEGER NOT NULL DEFAULT 0)")
    node.con.commit()

    @r.get("")
    def list_docs():
        items = []
        for s in _slugs():
            md = (DATA / f"{s}.md").read_text(encoding="utf-8")
            items.append({"slug": s, "title": _title(md, s), "draft": True})
        return {"disclaimer": DISCLAIMER, "items": items}

    @r.get("/{slug}")
    def get_doc(slug: str):
        if not SLUG_RE.match(slug) or not (DATA / f"{slug}.md").is_file():
            raise HTTPException(404, "not found")
        md = (DATA / f"{slug}.md").read_text(encoding="utf-8")
        return {"slug": slug, "title": _title(md, slug), "draft": True, "disclaimer": DISCLAIMER,
                "markdown": md, "html": md_to_html(md)}

    return r
