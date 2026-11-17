"""torahqa: Torah text quality checks (letters / words / verses / chapters per version vs. traditional counts)."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from fastapi import APIRouter

from ..ledger import now

NAV = {"label": "בדיקת טקסט", "href": "#/torahqa"}

CODE_VERSION = 1
BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]
HE_BOOKS = {"Genesis": "בראשית", "Exodus": "שמות", "Leviticus": "ויקרא", "Numbers": "במדבר", "Deuteronomy": "דברים"}
# Traditional counts (see docs/torahqa.md for sources and caveats).
STD_LETTERS = {"Genesis": 78064, "Exodus": 63529, "Leviticus": 44790, "Numbers": 63530, "Deuteronomy": 54892}
STD_VERSES = {"Genesis": 1534, "Exodus": 1209, "Leviticus": 859, "Numbers": 1288, "Deuteronomy": 955}
TOTAL_LETTERS = 304805
TOTAL_VERSES = 5845

_BRACKETS = re.compile(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|<[^>]*>")
_LETTER = re.compile(r"[א-ת]")
_WORD_SPLIT = re.compile(r"[\s־]+")  # whitespace and maqaf


def strip_text(t: str) -> str:
    """Remove bracketed/editorial notes and tags."""
    return _BRACKETS.sub(" ", unicodedata.normalize("NFC", t or ""))


def count_text(t: str) -> tuple[int, int]:
    """(letters, words) of one verse. Letters = Hebrew letters only (nikud, te'amim, maqaf ignored)."""
    s = strip_text(t)
    letters = len(_LETTER.findall(s))
    words = sum(1 for w in _WORD_SPLIT.split(s) if _LETTER.search(w))
    return letters, words


def _chapter_of(path: str) -> str:
    return path.split("@", 1)[0].split(".", 1)[0]


def analyze_version(con, vid: int) -> dict:
    letters = words = verses = 0
    chapters = set()
    for r in con.execute("SELECT path, text FROM segments WHERE version_id=?", (vid,)):
        l, w = count_text(r["text"])
        letters += l
        words += w
        verses += 1
        chapters.add(_chapter_of(r["path"]))
    return {"letters": letters, "words": words, "verses": verses, "chapters": len(chapters)}


def _is_translation(vt: str) -> bool:
    return bool(re.search(r"\[(yi|en|ar|ru|de|fr|es)\]|yiddish|translation", vt or "", re.I))


def compute(con) -> dict:
    ph = ",".join("?" * len(BOOKS))
    vers = con.execute(f"SELECT id,title,version_title,imported_at FROM versions WHERE title IN ({ph}) "
                       "AND language='he' ORDER BY title, version_title", BOOKS).fetchall()
    books = {b: [] for b in BOOKS}
    for v in vers:
        row = {"version_id": v["id"], "version_title": v["version_title"], "translation": _is_translation(v["version_title"])}
        row.update(analyze_version(con, v["id"]))
        row["delta_letters"] = row["letters"] - STD_LETTERS[v["title"]]
        row["delta_verses"] = row["verses"] - STD_VERSES[v["title"]]
        books[v["title"]].append(row)
    out_books = [{"title": b, "he_title": HE_BOOKS[b], "std_letters": STD_LETTERS[b], "std_verses": STD_VERSES[b],
                  "versions": books[b]} for b in BOOKS]
    # Totals only for version titles that cover all five books.
    names = {}
    for b in out_books:
        for r in b["versions"]:
            names.setdefault(r["version_title"], {})[b["title"]] = r
    totals = []
    for vt, per in sorted(names.items()):
        if len(per) != len(BOOKS):
            continue
        L = sum(r["letters"] for r in per.values())
        V = sum(r["verses"] for r in per.values())
        totals.append({"version_title": vt, "translation": per[BOOKS[0]]["translation"],
                       "letters": L, "words": sum(r["words"] for r in per.values()), "verses": V,
                       "chapters": sum(r["chapters"] for r in per.values()),
                       "delta_letters": L - TOTAL_LETTERS, "delta_verses": V - TOTAL_VERSES})
    return {"std": {"letters": TOTAL_LETTERS, "verses": TOTAL_VERSES}, "books": out_books, "totals": totals,
            "notes": "ספירה אוטומטית. הפרשים יכולים לנבוע מסימוני מהדיר, כתיב וקרי, הערות בסוגריים או חלוקת פסוקים שונה."}


def _ensure(con):
    con.execute("CREATE TABLE IF NOT EXISTS torahqa_cache (key TEXT PRIMARY KEY, computed_at TEXT NOT NULL, payload TEXT NOT NULL)")


def cache_key(con) -> str:
    ph = ",".join("?" * len(BOOKS))
    rows = con.execute(f"SELECT id, imported_at FROM versions WHERE title IN ({ph}) AND language='he' ORDER BY id", BOOKS).fetchall()
    s = f"v{CODE_VERSION}|" + "|".join(f"{r['id']}:{r['imported_at']}" for r in rows)
    return hashlib.sha256(s.encode()).hexdigest()


def get_report(con, refresh: bool = False) -> dict:
    _ensure(con)
    key = cache_key(con)
    if not refresh:
        r = con.execute("SELECT payload, computed_at FROM torahqa_cache WHERE key=?", (key,)).fetchone()
        if r:
            return json.loads(r["payload"]) | {"cached": True, "computed_at": r["computed_at"]}
    rep = compute(con)
    ts = now()
    con.execute("DELETE FROM torahqa_cache")
    con.execute("INSERT INTO torahqa_cache(key,computed_at,payload) VALUES (?,?,?)", (key, ts, json.dumps(rep, ensure_ascii=False)))
    con.commit()
    return rep | {"cached": False, "computed_at": ts}


def make_router(node) -> APIRouter:
    r = APIRouter()
    _ensure(node.con)

    @r.get("/api/torahqa")
    def torahqa(refresh: bool = False):
        return get_report(node.con, refresh)

    return r
