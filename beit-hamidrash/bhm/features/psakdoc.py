"""psakdoc: formal beit-din document view of a halachic DRAFT.

GET /api/psakdoc/{draft_id} -> structured document (header, file number, dates,
question, answer, resolved sources, reviews, valid dayan signatures, status,
mandatory notices). Never a ruling: unless approved by valid dayanim the
DRAFT_NOTICE (and AI_NOTICE for AI drafts) is always included.
"""
from __future__ import annotations

import os
from datetime import date, datetime

from fastapi import APIRouter, HTTPException

from .. import beitdin

STATUS_HE = {"draft": "טיוטה", "in_review": "בעיון", "approved": "אושר בחתימת דיין", "rejected": "נדחה"}

# ---------------------------------------------------------------- Hebrew date
_EPOCH = -1373427  # fixed day (R.D.) of 1 Tishri, year 1


def _leap(y: int) -> bool:
    return (7 * y + 1) % 19 < 7


def _elapsed(y: int) -> int:
    m = (235 * y - 234) // 19
    parts = 12084 + 13753 * m
    day = 29 * m + parts // 25920
    if (3 * (day + 1)) % 7 < 3:
        day += 1
    return day


def _new_year(y: int) -> int:
    ny0, ny1, ny2 = _elapsed(y - 1), _elapsed(y), _elapsed(y + 1)
    delay = 2 if ny2 - ny1 == 356 else (1 if ny1 - ny0 == 382 else 0)
    return _EPOCH + ny1 + delay


def _month_lengths(y: int) -> list[tuple[str, int]]:
    n = _new_year(y + 1) - _new_year(y)
    ms = [("תשרי", 30), ("חשוון", 30 if n % 10 == 5 else 29), ("כסלו", 29 if n % 10 == 3 else 30),
          ("טבת", 29), ("שבט", 30)]
    ms += [("אדר א׳", 30), ("אדר ב׳", 29)] if _leap(y) else [("אדר", 29)]
    return ms + [("ניסן", 30), ("אייר", 29), ("סיוון", 30), ("תמוז", 29), ("אב", 30), ("אלול", 29)]


def hebrew_date(d: date) -> tuple[int, str, int]:
    """(year, month name, day) for a Gregorian date. Pure computation, no libraries."""
    fixed = d.toordinal()
    y = int((fixed - _EPOCH) / 365.2468) + 1
    while _new_year(y + 1) <= fixed:
        y += 1
    while _new_year(y) > fixed:
        y -= 1
    rem = fixed - _new_year(y)
    for name, ln in _month_lengths(y):
        if rem < ln:
            return y, name, rem + 1
        rem -= ln
    raise ValueError("date out of range")


_GEM = [(400, "ת"), (300, "ש"), (200, "ר"), (100, "ק"), (90, "צ"), (80, "פ"), (70, "ע"), (60, "ס"),
        (50, "נ"), (40, "מ"), (30, "ל"), (20, "כ"), (10, "י"), (9, "ט"), (8, "ח"), (7, "ז"),
        (6, "ו"), (5, "ה"), (4, "ד"), (3, "ג"), (2, "ב"), (1, "א")]


def gematria(n: int) -> str:
    out = ""
    for v, c in _GEM:
        while n >= v:
            if n in (15, 16):
                out += "טו" if n == 15 else "טז"
                n = 0
                break
            out += c
            n -= v
    return out


def _fmt_gem(n: int) -> str:
    s = gematria(n)
    return s + "׳" if len(s) == 1 else s[:-1] + "״" + s[-1]


def hebrew_date_str(d: date) -> str:
    y, m, day = hebrew_date(d)
    return f"{_fmt_gem(day)} {m} {_fmt_gem(y % 1000)}"


# ---------------------------------------------------------------- document
def _resolve_source(con, ref: str) -> dict:
    out = {"ref": ref, "found": False, "versions": []}
    q = """SELECT s.ref, s.text, v.version_title, v.he_title, v.license
           FROM segments s JOIN versions v ON v.id=s.version_id WHERE {} ORDER BY v.tier, v.version_title, s.seq LIMIT {}"""
    try:
        rows = con.execute(q.format("s.ref=?", 3), (ref,)).fetchall()
        if not rows:
            rows = con.execute(q.format("s.ref LIKE ?", 5), (ref + ":%",)).fetchall()
    except Exception:
        rows = []
    out["versions"] = [{"ref": r["ref"], "text": r["text"], "version_title": r["version_title"],
                        "he_title": r["he_title"], "license": r["license"]} for r in rows]
    out["found"] = bool(rows)
    return out


def build_document(con, draft_id: str) -> dict:
    try:
        st = beitdin.draft_status(con, draft_id)
    except KeyError:
        raise HTTPException(404, "draft not found")
    if st["hidden"]:
        raise HTTPException(404, "draft not found")
    b = st["draft"]["body"]
    try:
        gd = datetime.fromisoformat(st["draft"]["ts"]).date()
    except Exception:
        gd = date.today()
    try:
        heb = hebrew_date_str(gd)
    except Exception:
        heb = None
    approved = st["status"] == "approved"
    notices = list(st["notices"])
    if not approved and beitdin.DRAFT_NOTICE not in notices:
        notices.insert(0, beitdin.DRAFT_NOTICE)
    if b.get("ai_generated") and beitdin.AI_NOTICE not in notices:
        notices.append(beitdin.AI_NOTICE)   # AI label stays even after human approval
    return {
        "id": draft_id,
        "header": {"blessing": 'בס"ד', "beit_din": os.environ.get("BHM_BEITDIN_NAME") or "בית הדין"},
        "file_number": draft_id[:8],
        "date": {"gregorian": gd.isoformat(), "hebrew": heb},
        "question": b.get("question", ""),
        "answer": b.get("answer", ""),
        "ai_generated": bool(b.get("ai_generated")),
        "author_name": st["author_name"],
        "sources": [_resolve_source(con, s) for s in b.get("sources", [])],
        "reviews": st["reviews"],
        "signatures": [{k: v for k, v in s.items() if k != "key"} for s in st["signatures"]],
        "status": st["status"],
        "status_he": STATUS_HE.get(st["status"], st["status"]),
        "approvals": st["approvals"],
        "required": st["required"],
        "approved": approved,
        "watermark": None if approved else "טיוטה",
        "notices": notices,
    }


def make_router(node) -> APIRouter:
    r = APIRouter()

    @r.get("/api/psakdoc/{draft_id}")
    def psakdoc(draft_id: str):
        return build_document(node.con, draft_id)

    return r
