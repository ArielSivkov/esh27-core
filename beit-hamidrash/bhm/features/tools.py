"""Study tools: gematria calculator (several methods), milui, atbash/albam, 231 gates.

Plain computation, no rulings. Routes: /api/tools/gematria, /api/tools/same.
"""
from __future__ import annotations

import re
from itertools import combinations

from fastapi import APIRouter, HTTPException

NAV = {"label": "כלים", "href": "#/tools"}

LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
VALS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400]
FINALS = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
BIG_FINALS = {"ך": 500, "ם": 600, "ן": 700, "ף": 800, "ץ": 900}
STD = dict(zip(LETTERS, VALS))
ORD = {c: i + 1 for i, c in enumerate(LETTERS)}
NAMES = {"א": "אלף", "ב": "בית", "ג": "גימל", "ד": "דלת", "ה": "הא", "ו": "ואו", "ז": "זין", "ח": "חית",
         "ט": "טית", "י": "יוד", "כ": "כף", "ל": "למד", "מ": "מם", "נ": "נון", "ס": "סמך", "ע": "עין",
         "פ": "פא", "צ": "צדי", "ק": "קוף", "ר": "ריש", "ש": "שין", "ת": "תיו"}
# The four fillings of the Name (yod always spelled יוד)
NAME_FILLINGS = {'ע"ב': {"ה": "הי", "ו": "ויו"}, 'ס"ג': {"ה": "הי", "ו": "ואו"},
                 'מ"ה': {"ה": "הא", "ו": "ואו"}, 'ב"ן': {"ה": "הה", "ו": "וו"}}
METHODS = ("standard", "big", "small", "ordinal", "kolel", "milui")
_NON = re.compile(r"[^א-ת]")
_WORD = re.compile(r"[א-ת]+")
_MARKS = re.compile("[֑-ׇ]")


def norm(s: str) -> str:
    """Hebrew letters only (nikud, cantillation, punctuation dropped); finals kept."""
    return _NON.sub("", _MARKS.sub("", s or ""))


def base(c: str) -> str:
    return FINALS.get(c, c)


def letter_value(c: str, method: str = "standard") -> int:
    b = base(c)
    if b not in STD:
        return 0
    if method == "big":
        return BIG_FINALS.get(c, STD[b])
    if method == "small":
        v = STD[b]
        return v if v < 10 else (v // 10 if v < 100 else v // 100)
    if method == "ordinal":
        return ORD[b]
    return STD[b]


def milui_letter(c: str, fill: dict | None = None) -> int:
    b = base(c)
    if b not in NAMES:
        return 0
    name = (fill or {}).get(b, NAMES[b])
    return sum(STD[x] for x in name)


def gematria(s: str, method: str = "standard") -> int:
    s = norm(s)
    if method == "kolel":
        return sum(STD[base(c)] for c in s) + len(s)
    if method == "milui":
        return sum(milui_letter(c) for c in s)
    return sum(letter_value(c, method) for c in s)


def all_methods(s: str) -> dict:
    return {m: gematria(s, m) for m in METHODS}


def milui_of_name(word: str = "יהוה") -> dict:
    return {k: sum(milui_letter(c, fill) for c in norm(word)) for k, fill in NAME_FILLINGS.items()}


_AT = dict(zip(LETTERS, reversed(LETTERS)))
_AL = {c: LETTERS[(i + 11) % 22] for i, c in enumerate(LETTERS)}


def _map(s: str, m: dict) -> str:
    return "".join(m.get(base(c), c) for c in norm(s))


def atbash(s: str) -> str:
    return _map(s, _AT)


def albam(s: str) -> str:
    return _map(s, _AL)


def gates() -> list[dict]:
    """All 231 two-letter gates (C(22,2))."""
    return [{"gate": a + b, "value": STD[a] + STD[b]} for a, b in combinations(LETTERS, 2)]


def words(text: str) -> list[str]:
    """Hebrew words of a text; nikud dropped, maqaf and punctuation separate words."""
    return _WORD.findall(_MARKS.sub("", text or ""))


def make_router(node) -> APIRouter:
    r = APIRouter(prefix="/api/tools")

    @r.get("/gematria")
    def api_gematria(ref: str, method: str = "standard"):
        if method not in METHODS:
            raise HTTPException(400, "unknown method")
        con = node.con
        segs = []
        row = con.execute("SELECT version_id FROM segments WHERE ref=? ORDER BY version_id LIMIT 1", (ref,)).fetchone()
        if row:
            segs = con.execute("SELECT ref,text FROM segments WHERE version_id=? AND ref=?", (row["version_id"], ref)).fetchall()
        else:
            row = con.execute("SELECT version_id FROM segments WHERE ref LIKE ? ORDER BY version_id LIMIT 1", (ref + ":%",)).fetchone()
            if row:
                segs = con.execute("SELECT ref,text FROM segments WHERE version_id=? AND ref LIKE ? ORDER BY seq LIMIT 100",
                                   (row["version_id"], ref + ":%")).fetchall()
        if not segs:
            raise HTTPException(404, "ref not found")
        out, total = [], 0
        for s in segs:
            ws = [{"word": w, "value": gematria(w, method)} for w in words(s["text"])]
            t = sum(w["value"] for w in ws)
            total += t
            out.append({"ref": s["ref"], "words": ws, "total": t})
        return {"ref": ref, "method": method, "segments": out, "total": total}

    @r.get("/same")
    def api_same(value: int, book: str, method: str = "standard", limit: int = 50):
        if method not in METHODS:
            raise HTTPException(400, "unknown method")
        limit = max(1, min(limit, 500))
        con = node.con
        v = con.execute("SELECT id FROM versions WHERE title=? OR he_title=? ORDER BY id LIMIT 1", (book, book)).fetchone()
        if not v:
            raise HTTPException(404, "book not found")
        found, distinct = [], set()
        for s in con.execute("SELECT ref,text FROM segments WHERE version_id=? ORDER BY seq", (v["id"],)):
            for w in words(s["text"]):
                if gematria(w, method) == value:
                    distinct.add(w)
                    if len(found) < limit:
                        found.append({"word": w, "ref": s["ref"]})
            if len(found) >= limit:
                break
        return {"value": value, "book": book, "method": method, "matches": found, "distinct": sorted(distinct)}

    return r
