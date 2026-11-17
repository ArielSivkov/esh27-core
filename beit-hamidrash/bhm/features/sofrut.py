"""sofrut: הלכות כתיבת ספר תורה (סת״ם), כעזר לימוד בלבד.

אין שום טקסט דיגיטלי שהוא ספר תורה, ובדיקה ממוחשבת היא לכל היותר כלי עזר למגיה אדם (ראו DISCLAIMER).

What this feature computes from the local library (all read-only, nothing is invented):

* parashiyot  : the open (פתוחה, {פ}/(פ)) and closed (סתומה, {ס}/(ס)) section breaks of the five books in
                two editions ("Miqra according to the Masorah" and "Tanach with Ta'amei Hamikra"), totals against the
                traditional 290 + 379 = 669, and the verses where the editions disagree.
* rambam      : Rambam's own list of sections (Tefillin, Mezuzah and Torah Scroll 8:4), parsed from the library text:
                the totals he states per book and the groups of incipits (the incipits are NOT mapped to verses).
* laws        : a structured checklist of the conditions of a kosher Sefer Torah, with sources and opinions
                (Rambam, Shulchan Arukh and glosses, Tur, commentaries, Keset HaSofer, Soferim); every ref is checked
                against the library and flagged when missing.
* shirot      : a layout illustration of Shirat HaYam (Exodus 15:1-19) and Ha'azinu (Deut 32:1-43) built from the
                line openers recorded by Rambam / Soferim, aligned to the actual verse text.  Illustration only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sqlite3
import unicodedata
from difflib import SequenceMatcher

from fastapi import APIRouter, HTTPException

from ..ledger import now
from .torahqa import BOOKS, HE_BOOKS, _LETTER, _WORD_SPLIT, strip_text  # reuse the torahqa normalisation

NAV = {"label": "הלכות סת״ם", "href": "#/sofrut"}

CODE_VERSION = 1

DISCLAIMER = ("אין שום טקסט דיגיטלי שהוא ספר תורה: ספר תורה נכתב בידי סופר מומחה, לשמה, על קלף בדיו, ונבדק בידי מגיה. "
              "כל בדיקה ממוחשבת כאן היא לכל היותר כלי עזר למגיה אדם, ואינה פוסקת ואינה מכשירה או פוסלת כלום. "
              "הנוסח, הפרשיות והסידור שהוצגו כאן הם מהמהדורות והמקורות שבספרייה, ולא אמת מידה סופית.")

MASORAH = "Miqra according to the Masorah"
LENINGRAD = "Tanach with Ta'amei Hamikra"
VERSIONS = {"masorah": MASORAH, "leningrad": LENINGRAD}
TRADITIONAL = {"open": 290, "closed": 379, "total": 669}
TRADITIONAL_NOTE = ("המנין המסורתי (290 פתוחות, 379 סתומות, 669 בסך הכול) הוא המנין שהרמב״ם עצמו מסכם בסוף הלכות ספר תורה פ״ח ה״ד; "
                    "הוא מופיע בטקסט הספרייה ונקרא ממנו כשהוא קיים.")

RAMBAM = "Mishneh Torah, Tefillin, Mezuzah and the Torah Scroll"
SECTIONS_REF = f"{RAMBAM} 8:4"
SA = "Shulchan Arukh, Yoreh De'ah"
TUR = "Tur, Yoreh De'ah"
TAZ = "Turei Zahav on Shulchan Arukh, Yoreh De'ah"
SHACH = "Siftei Kohen on Shulchan Arukh, Yoreh De'ah"
GRA = "Beur HaGra on Shulchan Arukh, Yoreh De'ah"
KS = "Keset HaSofer"
SOF = "Tractate Soferim"
SEFER_TORAH = "Tractate Sefer Torah"

# ---------------------------------------------------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------------------------------------------------
_TAG = re.compile(r"<[^>]+>")
_ENT = re.compile(r"&[a-zA-Z]+;|&#\d+;")
_FIN = str.maketrans("ךםןףץ", "כמנפצ")


def clean_text(t: str) -> str:
    """Tags and HTML entities removed, whitespace collapsed (display text)."""
    return re.sub(r"\s+", " ", _ENT.sub(" ", _TAG.sub(" ", t or ""))).strip()


def get_text(con, ref: str) -> str | None:
    """Fullest Hebrew text of a ref (several editions of one book may share the ref)."""
    r = con.execute("SELECT s.text FROM segments s JOIN versions v ON v.id=s.version_id "
                    "WHERE s.ref=? AND v.language='he' ORDER BY length(s.text) DESC LIMIT 1", (ref,)).fetchone()
    return r[0] if r else None


def words_of(text: str) -> list[str]:
    """Hebrew words of a verse, letters only (no nikud/te'amim/maqaf), editorial notes and section marks removed."""
    s = strip_text(_ENT.sub(" ", text or ""))
    out = []
    for tok in _WORD_SPLIT.split(s):
        w = "".join(_LETTER.findall(unicodedata.normalize("NFC", tok)))
        if w:
            out.append(w)
    return out


def letters_only(s: str) -> str:
    return "".join(_LETTER.findall(unicodedata.normalize("NFC", s or "")))


# ---------------------------------------------------------------------------------------------------------------------
# 1. section breaks (parashiyot)
# ---------------------------------------------------------------------------------------------------------------------
_MARK = re.compile(r"[\{\(]\s*([פס])\s*[\}\)]")


def find_breaks(text: str) -> list[tuple[str, str]]:
    """Section marks in one verse: [(kind, pos)] with kind 'open'|'closed' and pos 'end' (the break follows the verse)
    or 'mid' (the break is inside the verse, e.g. between the commandments of Ex 20:13)."""
    t = _ENT.sub(" ", text or "")
    out = []
    for m in _MARK.finditer(t):
        rest = strip_text(_MARK.sub("", t[m.end():]))
        out.append(("open" if m.group(1) == "פ" else "closed", "mid" if _LETTER.search(rest) else "end"))
    return out


def _find_vids(con, version_title: str) -> dict[str, int]:
    ph = ",".join("?" * len(BOOKS))
    rows = con.execute(f"SELECT title, id FROM versions WHERE version_title=? AND language='he' AND title IN ({ph}) ORDER BY id",
                       (version_title, *BOOKS)).fetchall()
    return {r[0]: r[1] for r in rows}


def book_breaks(con, vid: int) -> tuple[int, list[dict]]:
    verses, breaks = 0, []
    for ref, text in con.execute("SELECT ref, text FROM segments WHERE version_id=? ORDER BY seq", (vid,)):
        verses += 1
        mid = 0
        for kind, pos in find_breaks(text):
            slot = "end" if pos == "end" else f"mid{mid}"
            mid += pos == "mid"
            breaks.append({"ref": ref, "kind": kind, "slot": slot})
    return verses, breaks


def compare_breaks(a: dict[str, list[dict]], b: dict[str, list[dict]], order: dict[str, tuple[int, int]]) -> dict:
    """Diff of two {book: breaks} maps. Rows: the verses where the editions disagree."""
    rows = []
    for bi, book in enumerate(BOOKS):
        ka = {(x["ref"], x["slot"]): x["kind"] for x in a.get(book, [])}
        kb = {(x["ref"], x["slot"]): x["kind"] for x in b.get(book, [])}
        for key in set(ka) | set(kb):
            va, vb = ka.get(key), kb.get(key)
            if va == vb:
                continue
            typ = "kind_differs" if va and vb else ("only_masorah" if va else "only_leningrad")
            rows.append({"book": book, "ref": key[0], "slot": key[1], "masorah": va, "leningrad": vb, "type": typ})
    rows.sort(key=lambda r: (BOOKS.index(r["book"]), order.get(r["ref"], (0, 10 ** 9))[1], r["slot"]))
    by_book = {b_: sum(1 for r in rows if r["book"] == b_) for b_ in BOOKS}
    return {"count": len(rows), "by_type": {t: sum(1 for r in rows if r["type"] == t) for t in ("kind_differs", "only_masorah", "only_leningrad")},
            "by_book": by_book, "rows": rows}


def _summ(breaks: list[dict]) -> dict:
    o = sum(1 for x in breaks if x["kind"] == "open")
    c = sum(1 for x in breaks if x["kind"] == "closed")
    return {"open": o, "closed": c, "total": o + c, "mid_verse": sum(1 for x in breaks if x["slot"] != "end")}


def compute_parashiyot(con) -> dict:
    per, order = {}, {}
    for key, vt in VERSIONS.items():
        vids = _find_vids(con, vt)
        books = {}
        for bi, b in enumerate(BOOKS):
            if b not in vids:
                continue
            verses, br = book_breaks(con, vids[b])
            books[b] = {"verses": verses, "breaks": br}
            for i, (ref,) in enumerate(con.execute("SELECT ref FROM segments WHERE version_id=? ORDER BY seq", (vids[b],))):
                order.setdefault(ref, (bi, i))      # verse order, used to sort the diff
        per[key] = {"version_title": vt, "books": books}
    ram = rambam_sections(con)
    stated = {b["title"]: b["stated"] for b in ram.get("books", [])} if ram.get("found") else {}
    stated_total = ram.get("stated_total") if ram.get("found") else None
    trad = dict(TRADITIONAL, source=SECTIONS_REF if stated_total else "מנין מקובל", note=TRADITIONAL_NOTE)
    if stated_total and stated_total.get("open") is not None:
        trad.update(open=stated_total["open"], closed=stated_total["closed"], total=stated_total["total"])
    out_versions = []
    for key, d in per.items():
        rows, tot = [], {"open": 0, "closed": 0, "total": 0, "mid_verse": 0, "verses": 0}
        for b in BOOKS:
            if b not in d["books"]:
                continue
            s = _summ(d["books"][b]["breaks"])
            row = {"title": b, "he_title": HE_BOOKS[b], "verses": d["books"][b]["verses"], **s, "rambam": stated.get(b)}
            if stated.get(b) and stated[b].get("open") is not None:
                row["delta_open"] = s["open"] - stated[b]["open"]
                row["delta_closed"] = s["closed"] - stated[b]["closed"]
            rows.append(row)
            for k in tot:
                tot[k] += row[k]
        complete = len(rows) == len(BOOKS)
        tot.update(delta_open=tot["open"] - trad["open"], delta_closed=tot["closed"] - trad["closed"],
                   delta_total=tot["total"] - trad["total"])
        out_versions.append({"key": key, "version_title": d["version_title"], "present": bool(rows), "complete": complete,
                             "books": rows, "totals": tot})
    a = {b: v["breaks"] for b, v in per["masorah"]["books"].items()}
    b_ = {b: v["breaks"] for b, v in per["leningrad"]["books"].items()}
    both = bool(a) and bool(b_)
    diff = compare_breaks(a, b_, order) if both else {"count": 0, "by_type": {}, "by_book": {}, "rows": []}
    notes = ["הסימונים נקראים מהטקסט: {פ}/{ס} במהדורת המסורה ו-(פ)/(ס) במהדורת התגיות; פרשה בתוך פסוק (למשל עשרת הדברות) נספרת בפני עצמה ומסומנת mid.",
             "הפרש מול המנין המסורתי אינו הכרעה: מהדורות נבדלות בפרשיות ספורות, והרמב״ם עצמו מנה לפי כתר ארם צובה (המצרי)."]
    return {"available": bool(a or b_), "traditional": trad, "rambam_found": bool(ram.get("found")), "versions": out_versions,
            "diff": diff, "notes": notes, "disclaimer": DISCLAIMER}


# ---------------------------------------------------------------------------------------------------------------------
# 2. Rambam's own list of sections (Tefillin, Mezuzah and Torah Scroll 8:4)
# ---------------------------------------------------------------------------------------------------------------------
_UNITS = {"אחד": 1, "אחת": 1, "שתים": 2, "שנים": 2, "שתי": 2, "שני": 2, "שלש": 3, "שלשה": 3, "שלושה": 3, "ארבע": 4, "ארבעה": 4,
          "חמש": 5, "חמשה": 5, "שש": 6, "ששה": 6, "שבע": 7, "שבעה": 7, "שמנה": 8, "שמונה": 8, "תשע": 9, "תשעה": 9}
_TENS = {"עשר": 10, "עשרה": 10, "עשרים": 20, "שלשים": 30, "ארבעים": 40, "חמשים": 50, "ששים": 60, "שבעים": 70, "שמונים": 80,
         "שמנים": 80, "תשעים": 90}
_NUMWORDS = set(_UNITS) | set(_TENS) | {"מאה", "מאתים", "מאות"}


def _numtok(tok: str) -> str | None:
    w = tok.strip(" .,:;()[]")
    if w in _NUMWORDS:
        return w
    if w.startswith("ו") and w[1:] in _NUMWORDS:
        return w[1:]
    return None


def heb_number(s: str) -> int | None:
    """Hebrew number words -> int ('מאה וחמשים ושמונה' -> 158); None if any token is not a number word."""
    total = cur = 0
    seen = False
    for tok in s.split():
        w = _numtok(tok)
        if w is None:
            return None
        seen = True
        if w == "מאות":
            if not cur:
                return None
            total, cur = total + cur * 100, 0
        elif w in ("מאה", "מאתים"):
            total += 100 if w == "מאה" else 200
        else:
            cur += _UNITS.get(w) or _TENS[w]
    return total + cur if seen else None


_BOOK_HDR = re.compile(r"ספר (בראשית|ואלה שמות|ויקרא|במדבר סיני|אלה הדברים)\s*:")
_HDR_BOOK = {"בראשית": "Genesis", "ואלה שמות": "Exodus", "ויקרא": "Leviticus", "במדבר סיני": "Numbers", "אלה הדברים": "Deuteronomy"}
_STATED = re.compile(r"מנין הפתוחות(?: של (?P<scope>ספר זה|כל התורה))? (?P<o>.+?) (?:ו?מנין )?ו?הסתומות (?P<c>.+?) הכל (?P<t>.+?)"
                     r"(?: פרשיות)?(?=\s*:|\s+מנין הפתוחות|\s*$)")
_QUANT = {"שתיהן": 2, "שתיהם": 2, "שלשתן": 3, "שלשתם": 3, "ארבעתן": 4, "ארבעתם": 4, "חמשתן": 5, "חמשתם": 5, "כולן": None, "כולם": None}
_TYPES = {"פתוחה": "open", "פתוחות": "open", "סתומה": "closed", "סתומות": "closed"}


def _stated(m: re.Match) -> dict:
    o, c, t = heb_number(m.group("o")), heb_number(m.group("c")), heb_number(m.group("t"))
    return {"open": o, "closed": c, "total": t, "consistent": None not in (o, c, t) and o + c == t}


def _parse_groups(body: str) -> list[dict]:
    """Groups of incipits as Rambam lists them: 'X Y Z שלשתן סתומות'. count is the number of sections in the group
    when he states it (singular, שתיהן, שלשתן, ..., or 'והן N'), else None (e.g. 'כולן' alone)."""
    toks = [t.replace("(", "").replace(")", "") for t in body.replace(":", " ").split()]
    groups, buf, i = [], [], 0
    while i < len(toks):
        tk = toks[i]
        i += 1
        if tk not in _TYPES:
            buf.append(tk)
            continue
        count, quant = 1 if tk.endswith("ה") else None, False
        if buf and buf[-1] in _QUANT:
            count, quant = _QUANT[buf.pop()], True
            if count is None:                       # 'כולן': maybe 'אחת עשרה פרשיות אלו כולן סתומות' before it
                j = len(buf)
                if j and buf[j - 1] == "אלו":
                    j -= 1
                if j and buf[j - 1] == "פרשיות":
                    j -= 1
                    k = j
                    while k and _numtok(buf[k - 1]):
                        k -= 1
                    n = heb_number(" ".join(buf[k:j])) if k < j else None
                    if n:
                        count = n
                        del buf[k:]
        elif tk.endswith("ות"):
            quant = True
        if quant and count is None and i < len(toks) and toks[i] in ("והן", "והם", "הן", "הם"):   # '... כולן סתומות והן שבע'
            k = i + 1
            while k < len(toks) and _numtok(toks[k]) and not (toks[k] == "עשר" and toks[k + 1:k + 2] == ["תעשר"]):  # 'עשר תעשר' is an incipit
                k += 1
            n = heb_number(" ".join(toks[i + 1:k])) if k > i + 1 else None
            if n:
                count, i = n, k
                if i < len(toks) and toks[i] == "פרשיות":
                    i += 1
        elif quant and count is None and i + 1 < len(toks) and toks[i].startswith("ה") and _numtok(toks[i][1:]) and toks[i + 1] == "פרשיות":
            count, i = heb_number(toks[i][1:]), i + 2                                     # '... כולן סתומות השמונה פרשיות'
        groups.append({"kind": _TYPES[tk], "count": count, "incipits": " ".join(buf)})
        buf = []
    return groups


def rambam_sections(con) -> dict:
    """Parse Rambam's own list of sections from the library text. found=False (with the reason) when it is not there."""
    raw = get_text(con, SECTIONS_REF)
    if not raw:
        return {"found": False, "ref": SECTIONS_REF, "reason": "הקטע לא נמצא בספרייה", "books": [], "disclaimer": DISCLAIMER}
    return parse_rambam_sections(clean_text(raw))


def parse_rambam_sections(text: str) -> dict:
    hdrs = list(_BOOK_HDR.finditer(text))
    if len(hdrs) < 5 or not _STATED.search(text):
        return {"found": False, "ref": SECTIONS_REF, "reason": "ברשימה שבקטע אין כותרות ספרים ומנינים (ייתכן שהמהדורה בספרייה אינה כוללת את רשימת הפרשיות)",
                "books": [], "disclaimer": DISCLAIMER}
    books, total = [], None
    for i, h in enumerate(hdrs):
        end = hdrs[i + 1].start() if i + 1 < len(hdrs) else len(text)
        body = text[h.end():end]
        stated = list(_STATED.finditer(body))
        title = _HDR_BOOK[h.group(1)]
        first = next((m for m in stated if m.group("scope") != "כל התורה"), None)
        for m in stated:
            if m.group("scope") == "כל התורה":
                total = _stated(m)
        groups = _parse_groups(body[:first.start()] if first else body)
        known_o = sum(g["count"] or 0 for g in groups if g["kind"] == "open")
        known_c = sum(g["count"] or 0 for g in groups if g["kind"] == "closed")
        books.append({"title": title, "he_title": HE_BOOKS[title], "stated": _stated(first) if first else {"open": None, "closed": None, "total": None, "consistent": False},
                      "groups": groups,
                      "parsed": {"groups": len(groups), "open_groups": sum(g["kind"] == "open" for g in groups),
                                 "closed_groups": sum(g["kind"] == "closed" for g in groups),
                                 "counted_open": known_o, "counted_closed": known_c,
                                 "groups_without_count": sum(g["count"] is None for g in groups)}})
    sums = {k: sum(b["stated"][k] or 0 for b in books) for k in ("open", "closed", "total")}
    return {"found": True, "ref": SECTIONS_REF, "books": books, "stated_total": total, "sum_of_books": sums,
            "sum_matches_stated_total": bool(total) and all(total.get(k) == sums[k] for k in sums),
            "note": ("המנינים לכל ספר ולכל התורה נלקחו כלשונם מהטקסט. הרשימה עצמה מוצגת כקבוצות של פתיחות פרשיות (incipits) כפי שהרמב״ם כותב, "
                     "ולא נמפתה לפסוקים. קבוצות עם count=null אינן מציינות מספר ('כולן סתומות')."),
            "disclaimer": DISCLAIMER}


# ---------------------------------------------------------------------------------------------------------------------
# 3. the laws checklist
# ---------------------------------------------------------------------------------------------------------------------
def V(who: str, ref: str | None, gist: str) -> dict:
    return {"who": who, "ref": ref, "gist": gist}


_R = RAMBAM
LAWS: list[dict] = [
    {"id": "pasul20", "title": "עשרים הדברים הפוסלים (רשימת הרמב״ם)", "level": "מעכב",
     "summary": "הרמב״ם מונה עשרים דברים שכל אחד מהם פוסל ספר תורה, והופך אותו ל״חומש מן החומשין״. שאר הפרטים (מידות, ריוחים, מנין השיטין, תגין) הם למצוה מן המובחר ולא לעכב.",
     "refs": [f"{_R} 10:1", f"{_R} 7:9", f"{_R} 7:11"],
     "views": [V("רמב״ם", f"{_R} 7:9", "שינה במידות, בשיטין, בריוחים או בתגין, ובלבד שלא הדביק אות, לא חיסר, לא הותיר, לא הפסיד צורת אות ולא שינה בפתוחות וסתומות: כשר."),
               V("רמב״ם", f"{_R} 7:11", "מלא וחסר, קרי וכתיב כקריאתו, פרשה פתוחה כסתומה וסתומה כפתוחה, שירה כשאר הכתב: פסול לגמרי.")],
     "digital": {"level": "partial", "text": "מבין העשרים אפשר לבדוק בעזרת מחשב רק חסר ויתר אותיות (מול נוסח ייחוס), פרשיות פתוחות וסתומות (איפה, לא כמה ריוח), ושפת הכתב. עור, עיבוד, לשמה, דיו, שרטוט, צורת אות ותפירה אי אפשר לבדוק דיגיטלית."}},
    {"id": "writer", "title": "כותב כשר", "level": "מעכב",
     "summary": "ספר תורה שכתבו אפיקורוס, כותי, ישראל מומר, מוסר, עבד, אשה או קטן פסול. הסופר חייב להיות מי שמצווה על הקשירה ומאמין בה.",
     "refs": [f"{_R} 1:13", f"{SA} 281:3", f"{KS} 1:2"],
     "views": [V("רמב״ם", f"{_R} 1:13", "נמצא ביד כותי ואינו יודע מי כתבו: כשר, ואין לוקחים מן הכותים."),
               V("שולחן ערוך", f"{SA} 281:1", "נמצא ביד כנעני ואינו יודע מי כתבו: יש מכשירים ויש אומרים יגנז, והציבור חייבים לקנותו ולגנזו."),
               V("רמ״א / מרדכי", f"{SA} 281:4", "ממזר: יש פוסלים."),
               V("קסת הסופר", f"{KS} 1:2", "נדרש ״גדול ממש״: שתי שערות לאחר י״ג שנה, ובספק פסול עד שיעברו עליו רוב שנותיו או סימני סריס.")],
     "digital": {"level": "no", "text": "זהות הכותב, אמונתו וגילו אינם דבר שמחשב יכול לבדוק או להעיד עליו."}},
    {"id": "hide_species", "title": "העור: ממין בהמה, חיה ועוף טהורים", "level": "מעכב",
     "summary": "כותבים רק על עור בהמה חיה ועוף טהורים, ואפילו מנבלות וטריפות שלהם. לא על עור טמא ולא על עור דג.",
     "refs": [f"{_R} 1:10", f"{SA} 271:1", f"{KS} 2:1"],
     "views": [V("רמב״ם", f"{_R} 1:10", "אין כותבים על עור דג טהור מפני הזוהמה שאינה פוסקת בעיבודו."),
               V("קסת הסופר", f"{KS} 2:1", "גם הגידים והשערות רק מן המינים המותרים; סדר עדיפות לעורות: עור שליל, אחר כך עוף, חיה, בהמה ואחר כך נבלה.")],
     "digital": {"level": "no", "text": "מין העור הוא עובדה פיזית של החומר; אין לה ייצוג בטקסט."}},
    {"id": "gevil_klaf", "title": "גויל או קלף, ובאיזה צד כותבים", "level": "מעכב",
     "summary": "הלכה למשה מסיני: ספר תורה על גויל במקום שיער. אם כתב על קלף כשר, ובלבד שכתב בצד הפנימי (כלפי הבשר). הכותב מקצת על גויל ומקצת על קלף, פסול. דוכסוסטוס פסול.",
     "refs": [f"{_R} 1:8", f"{_R} 1:9", f"{SA} 271:3"],
     "views": [V("רמב״ם", f"{_R} 1:9", "גויל נאמר רק למעט דוכסוסטוס; ספר שנכתב על קלף כשר."),
               V("שולחן ערוך", f"{SA} 271:4", "מקצתו על גויל ומקצתו על קלף: פסול. חציו גויל וחציו צבאים: כשר."),
               V("רמ״א (בשם ר״י מינץ, אור זרוע)", f"{SA} 271:3", "הקלפים שלנו מובחרים מגויל, וכותבים עליהם לכתחלה לצד בשר; כתב במקום שיער פסול, ויש מקילים (טור וב״י).")],
     "digital": {"level": "no", "text": "סוג העור וצדו אינם נראים בטקסט."}},
    {"id": "hide_lishmah", "title": "עיבוד העור לשם ספר תורה", "level": "מעכב",
     "summary": "העור צריך להיות מעובד לשם ספר תורה. עיבוד שלא לשמו פוסל.",
     "refs": [f"{_R} 1:11", f"{SA} 271:1", f"{TUR} 271:1"],
     "views": [V("רמב״ם", f"{_R} 1:11", "עיבדו כותי פסול, אף שאמרו לו לעבד לשם ספר, כי כותי על דעת עצמו הוא עושה."),
               V("שולחן ערוך", f"{SA} 271:1", "העיבוד בידי ישראל, והוא אומר בתחילת העיבוד ״עורות אלו אני מעבד לשם ספר תורה״."),
               V("רמ״א (טור בשם ר״ב, ב״י)", f"{SA} 271:1", "עיבד עכו״ם: הישראל מסייע מעט בתחילה, אומר שהוא לשם קדושה, ומסמן את העורות."),
               V("טור", f"{TUR} 271:1", "תיקון הקלף ושרטוטו אינם צריכים לשמה; ר״ב נסתפק אם צריך לומר בפיו.")],
     "digital": {"level": "no", "text": "כוונת העיבוד ועשייתו אינן ניתנות לבדיקה דיגיטלית."}},
    {"id": "ink", "title": "דיו שחור", "level": "מעכב",
     "summary": "הלכה למשה מסיני שכותבים בדיו; צבעים אחרים (אדום, ירוק) ואפילו זהב פוסלים אפילו באות אחת. הדיו המובחר: פיח, שרף ודבש, שרוי במי עפצים.",
     "refs": [f"{_R} 1:4", f"{SA} 271:6", f"{KS} 3:1"],
     "views": [V("רמב״ם", f"{_R} 1:5", "ההלכה מיעטה שאר צבעונים; כתב אות אחת בצבע או בזהב: פסול."),
               V("שולחן ערוך", f"{SA} 271:6", "דיו מעשן שמנים שרוי במי עפצים; מי עפצא וקנקנתום כשר."),
               V("רמ״א (על פי הזוהר)", f"{SA} 271:6", "לכתחלה להזהר שיהיה הדיו מדברים הבאים מן העץ."),
               V("קסת הסופר", f"{KS} 3:1", "היום נוהגים גם לכתחלה במי עפצים, קומום וקנקנתום, ובלבד שהדיו שחור בתכלית.")],
     "digital": {"level": "no", "text": "הדיו והשחרות אינם ניתנים לבדיקה דיגיטלית."}},
    {"id": "ruling", "title": "שרטוט", "level": "מעכב",
     "summary": "ספר תורה צריך שרטוט, וכתב בלא שרטוט פסול. לא משרטטים בעופרת ובדומה לה שצובע.",
     "refs": [f"{_R} 1:12", f"{SA} 271:5", f"{SA} 284:2"],
     "views": [V("רמב״ם", f"{_R} 7:16", "מותר לכתוב שלש תיבות בלא שרטוט, יותר מזה אסור."),
               V("טור", f"{TUR} 284:1", "נחלקו: יש שהתירו שתי תיבות ואסרו שלש; יש שהתירו שלש ואסרו ארבע (וכן הרמב״ם); בעל הלכות גדולות והרא״ש אסרו שלש והתירו שתים."),
               V("שולחן ערוך", f"{SA} 284:2", "אסור לכתוב שלש תיבות מפסוק בלא שרטוט בכתב אשורית.")],
     "digital": {"level": "no", "text": "הקווים על הקלף אינם נראים בטקסט."}},
    {"id": "copy", "title": "כתיבה מן הכתב (ספר מוגה לפניו)", "level": "מעכב",
     "summary": "בספר תורה אסור לכתוב אפילו אות אחת שלא מן הכתב, וצריך לקרוא כל תיבה בפיו לפני כתיבתה.",
     "refs": [f"{_R} 1:12", f"{SA} 274:2"],
     "views": [V("רמב״ם", f"{_R} 1:12", "תפילין ומזוזה מותר לכתוב מן הזכרון, אבל ספר תורה אסור אפילו אות אחת שלא מן הכתב."),
               V("שולחן ערוך", f"{SA} 274:2", "צריך שיהיה לפניו ספר אחר שיעתיק ממנו, ולקרוא כל תיבה בפיו קודם כתיבתה.")],
     "digital": {"level": "partial", "text": "מחשב יכול לשמש ספר ייחוס להשוואה ולהצגת הנוסח, אבל אינו תחליף ל״ספר אחר מוגה״ שמעתיק ממנו הסופר, ולא להשוואת מגיה."}},
    {"id": "lishmah", "title": "כתיבה לשם קדושת ספר תורה", "level": "מעכב",
     "summary": "הסופר אומר בפיו בתחילת הכתיבה ״אני כותב לשם קדושת ספר תורה״, ודי לכל הספר (פרט לשמות הקדושים).",
     "refs": [f"{SA} 274:1", f"{TUR} 274:1", f"{KS} 4:1"],
     "views": [V("שולחן ערוך / טור", f"{SA} 274:1", "אומר בפיו בתחלת הספר; הטור מוסיף שאם לא עשה כן פסול."),
               V("קסת הסופר", f"{KS} 4:1", "חשב בלב ולא הוציא בפיו: יש פוסלים אפילו בדיעבד, ויש מכשירים בדיעבד, וכן נראה עיקר.")],
     "digital": {"level": "no", "text": "הכוונה והאמירה אינן ניתנות לבדיקה דיגיטלית."}},
    {"id": "names", "title": "שמות הקדושים: לשם קדושת השם, ותיקון שכחה", "level": "מעכב",
     "summary": "בכל שם מהשמות שאינם נמחקים צריך לכוון שכותבו לשם קדושת השם. שכח לכתוב שם שלם: תולה בין השיטין; מקצתו: פסול.",
     "refs": [f"{_R} 1:15", f"{SA} 276:2", f"{KS} 10:1"],
     "views": [V("רמב״ם", f"{_R} 1:15", "כתב אזכרה בלא כוונה פסול; אפילו מלך ישראל שואל בשלומו לא ישיבנו, ושנים או שלשה שמות מפסיק ביניהם."),
               V("רמב״ם", f"{_R} 1:16", "שכח לכתוב את השם כולו תולה בין השיטות; מקצת השם בשיטה ומקצתו תלוי: פסול."),
               V("שולחן ערוך", f"{SA} 276:6", "שכח לכתוב השם כולו תולה בין השיטות, אבל מקצת השם בשיטה ומקצתו תלוי פסול."),
               V("רמ״א (ב״י בשם רשב״ץ)", f"{SA} 276:2", "כתב שם אלהים אחרים לשם קדושה: אינו פסול."),
               V("שולחן ערוך", f"{SA} 276:5", "כתב האזכרות בדיו וזרק עליהם זהב: פסול.")],
     "digital": {"level": "partial", "text": "מחשב יכול לאתר היכן מופיעים השמות בנוסח, כרשימת תזכורת לסופר ולמגיה. אי אפשר לבדוק כוונה, ולא אם נכתבו כראוי."}},
    {"id": "letters_complete", "title": "אין חסר ואין יתר אות אחת", "level": "מעכב",
     "summary": "חסר או הוסיף אפילו אות אחת פסול. מלא במקום חסר או חסר במקום מלא פסול, וכן כתיבת קרי במקום כתיב.",
     "refs": [f"{_R} 10:1", f"{_R} 7:11", f"{SA} 275:6"],
     "views": [V("רמב״ם", f"{_R} 7:11", "כתב המלא חסר או החסר מלא, או מלה שהיא קרי וכתבה כקריאתה (ישכבנה במקום ישגלנה): פסול."),
               V("שולחן ערוך", f"{SA} 275:6", "אותו דין, עם הדוגמאות ״ישכבנה/ישגלנה״ ו״ובטחורים/ובעפולים״."),
               V("רמב״ם", f"{_R} 1:2", "ספר תורה שחיסר אפילו אות אחת פסול.")],
     "digital": {"level": "yes", "text": "זה התחום שבו מחשב יכול לעזור: ספירת אותיות והשוואה אות באות לנוסח ייחוס (ראו עמוד בדיקת הטקסט, torahqa: 304,805 אותיות במנין המסורתי). אבל הכרעה איזה נוסח (מלא וחסר, קרי וכתיב, מנהגי עדות) היא של מגיה אדם, ולא של תוכנה."}},
    {"id": "letter_shapes", "title": "צורת האותיות", "level": "מעכב",
     "summary": "אות שנפסדה צורתה עד שאינה נקראת או דומה לאות אחרת פוסלת. תינוק שאינו חכם ולא טיפש צריך להיות מסוגל לקרוא אותה.",
     "refs": [f"{_R} 10:1", f"{SA} 274:5", f"{KS} 5:1"],
     "views": [V("רמב״ם", f"{_R} 1:19", "כל אות שאין התינוק שאינו לא חכם ולא סכל יכול לקרותה פסול."),
               V("שולחן ערוך", f"{SA} 274:3", "כתב אל״ף למ״ד ביחד כצורת ליגטורה: אינו כשר."),
               V("קסת הסופר", f"{KS} 5:1", "לכתחלה בתמונות האותיות שקיבלו מן הראשונים; שינה לא פסל אלא אם הפסיד צורת האות.")],
     "digital": {"level": "no", "text": "צורת אות על קלף אינה דבר שהטקסט הדיגיטלי מייצג. זיהוי תמונה יכול אולי לסייע, ואינו נבדק או מוגדר כאן."}},
    {"id": "ketiva_tama", "title": "כתיבה תמה: לא נוגעת ולא מופרדת", "level": "מעכב",
     "summary": "כל אות מוקפת גויל מארבע רוחותיה. אות שנגעה באות, או תיבה שנראית כשתי תיבות או שתי תיבות כאחת, פוסלות.",
     "refs": [f"{_R} 10:1", f"{SA} 274:4", f"{KS} 7:1"],
     "views": [V("רמב״ם", f"{_R} 7:4", "בין תיבה לתיבה כמלא אות קטנה, בין אות לאות כחוט השערה, בין שיטה לשיטה כמלא שיטה."),
               V("שולחן ערוך", f"{SA} 274:4", "שינה והרחיק עד שהתיבה נראית כשתים, או קירב עד שנראות כאחת: פסול."),
               V("קסת הסופר", f"{KS} 7:1", "אפילו בתגין לא יגעו; תינוק שאינו לא חכם ולא טיפש הוא הבוחן.")],
     "digital": {"level": "no", "text": "ריווח וצמידות אותיות הם עניין של כתב היד ולא של הנוסח."}},
    {"id": "no_nikud", "title": "בלא ניקוד ובלא הפסק פסוקים", "level": "מעכב",
     "summary": "ספר המנוקד פסול, ואפילו הסירו את הניקוד. כן ספר שיש בו פיסוק פסוקים.",
     "refs": [f"{SA} 274:7"],
     "views": [V("שולחן ערוך", f"{SA} 274:7", "ספר המנוקד פסול ואפילו הסירו ממנו הניקוד; כן ספר שיש בו פיסוק פסוקים."),
               V("רמ״א (ריב״ש)", f"{SA} 274:7", "ודוקא שעשה הפסק בדיו; אם הניח אויר בין הפסוקים בפחות משיעור פרשה: כשר.")],
     "digital": {"level": "partial", "text": "בטקסט דיגיטלי אפשר לזהות ניקוד, טעמים וסימני סוף פסוק, אך זו תכונה של התמלול ולא של ספר תורה."}},
    {"id": "dimensions", "title": "מידות הספר: ארכו כהיקפו", "level": "למצוה",
     "summary": "אין עושים ספר תורה שארכו יותר על היקפו או להפך. בגויל שישה טפחים, ואם שינה ויצא ארכו כהיקפו, הרי זה כמצוה.",
     "refs": [f"{_R} 9:1", f"{SA} 272:1", f"{KS} 13:1"],
     "views": [V("רמב״ם", f"{_R} 9:1", "ארכו כהיקפו; בגויל ששה טפחים, ובקלף פחות או יותר."),
               V("טור (בשם הרא״ש)", f"{SA} 272:1", "העמוד שבתוך הספר מצטרף להיקף."),
               V("קסת הסופר", f"{KS} 13:1", "יש אומרים שהעמוד מצטרף (תוספות והרא״ש) ויש אומרים שאינו; ודורש הידור ״זה אלי ואנוהו״.")],
     "digital": {"level": "no", "text": "המידות הפיזיות אינן בטקסט. אפשר לכל היותר לתכנן חשבון דפים לפי ספירת אותיות (הרמב״ם פ״ט)."}},
    {"id": "lines_columns", "title": "אורך שיטה ומנין השיטין בדף", "level": "למצוה",
     "summary": "שיטה: שלשים אותיות (״למשפחותיכם״ שלש פעמים). בכל דף לא פחות מ-48 ולא יותר מ-60 שיטין.",
     "refs": [f"{_R} 7:4", f"{_R} 7:10", f"{SA} 275:6"],
     "views": [V("רמב״ם", f"{_R} 7:4", "לא תהא שיטה קצרה מזה כדי שלא יהא הדף כאגרת, ולא ארוכה כדי שלא יהיו עיניו משוטטות."),
               V("קסת הסופר", f"{KS} 13:2", "דוקא בכתיבה דקה; בכתיבה גסה הכל לפי הנוי."),
               V("רמ״א (טור)", f"{SA} 275:6", "מנין השיטין לא פחות ממ״ח, ויש אומרים מ״ב, ולא יותר מס׳."),
               V("ט״ז", f"{TAZ} 275:8", "מ״ח כנגד מ״ח מסעות, ו-ס׳ כנגד שישים ריבוא; וסימן למ״ב: ״בם סיני בקודש״ (ט״ז ס״ק ט).")],
     "digital": {"level": "partial", "text": "אפשר לחשב כמה אותיות ושיטות יוצאות מכל טקסט וגודל כתב נתון. אין זה בודק כתב יד."}},
    {"id": "margins_books", "title": "גליון, ריוחים ומעבר בין חומשים", "level": "למצוה",
     "summary": "ארבע שיטין פנויות בין חומש לחומש, ותחילת החומש מתחילת שיטה חמישית. גליון: ארבע אצבעות למטה, שלש למעלה, שתים בין דף לדף. גומרים באמצע שיטה בסוף הדף.",
     "refs": [f"{_R} 7:7", f"{_R} 9:2", f"{SA} 273:1"],
     "views": [V("קסת הסופר", f"{KS} 14:1", "ארבע שיטין פנויות בין חומש לחומש, והחומש מתחיל בתחלת שיטה חמישית; גליון ארבע אצבעות למטה ושלש למעלה."),
               V("רמב״ם", f"{_R} 9:2", "כל השיעורים האלו למצוה, ואם חסר או הותיר לא פסל."),
               V("שולחן ערוך", f"{SA} 272:4", "כשיגמור את התורה צריך שיגמור באמצע שיטה שבסוף הדף, לעיני כל ישראל.")],
     "digital": {"level": "no", "text": "ריוחים וגליונות הם פיזיים; אפשר רק לדעת היכן מתחיל כל חומש בנוסח."}},
    {"id": "sections", "title": "פרשיות פתוחות וסתומות", "level": "מעכב",
     "summary": "פרשה פתוחה שעשאה סתומה או סתומה שעשאה פתוחה פסולה (לרמב״ם אין לה תקנה אלא לסלק את הדף). הרמב״ם מונה בסוף פ״ח את כל הפרשיות: 290 פתוחות ו-379 סתומות, בסך 669. פתוחה מתחילה בראש שיטה, סתומה באמצע שיטה, וריוח כתשע אותיות.",
     "refs": [f"{_R} 8:1", f"{_R} 8:4", f"{SA} 275:2"],
     "views": [V("רמב״ם", f"{_R} 8:1", "פתוחה מתחילה תמיד בתחלת שיטה (אחרי ריוח של תשע אותיות או שיטה פנויה)."),
               V("רמב״ם", f"{_R} 8:2", "סתומה מתחילה תמיד באמצע שיטה."),
               V("רמב״ם", f"{_R} 8:3", "שינה בריוח הפרשיות, או הניח פנוי במקום שאין פרשה: פסול, ואין תקנה אלא לסלק את הדף."),
               V("רא״ש (בטור)", f"{TUR} 275:1", "תיקון מועיל, כמו בטעות חסרות ויתרות; אינו יודע איך לתקן עוות הפתוחות."),
               V("שולחן ערוך", f"{SA} 275:2", "יש מחלוקת בין הרמב״ם והרא״ש בצורת פתוחה וסתומה, וירא שמים יוצא ידי כולם: פתוחה מתחילה בראש שיטה אחרי ריוח תשע אותיות בסוף הקודמת, סתומה מתחילה בסוף שיטה אחרי ריוח תשע אותיות בתחילתה."),
               V("רמ״א", f"{SA} 275:2", "אם אי אפשר לכוון, לא יסור מדברי הרמב״ם, ובכל זאת ספר שאינו כרמב״ם אין לפסלו."),
               V("ט״ז", f"{TAZ} 275:5", "שתי מחלוקות בין הרמב״ם והרא״ש: מה נחשב מקום פנוי בתחילת שיטה, והשיטה הריקה: מה שהוא פתוחה לרמב״ם הוא סתומה להרא״ש."),
               V("קסת הסופר", f"{KS} 15:1", "נחלקו הרמב״ם והרא״ש, וירא שמים מדקדק לעשות באופן הכשר לכולם; בדיעבד די בשיעור תשע יודי״ן."),
               V("ש״ך", f"{SHACH} 275:5:1", "מצטט את הרמב״ם פ״ח ה״א-ה״ב כעיקר."),
               V("מסכת סופרים", f"{SOF} 1:14", "שיעור הריוח: כדי לכתוב שם של שלש אותיות (לעומת תשע אותיות אצל הרמב״ם והשו״ע)."),
               V("ט״ז (על הטור)", f"{TAZ} 275:4", "הטור: בסתומה שלש אותיות ובפתוחה תשע; להלכה כשו״ע (תשע) כדעת רוב הפוסקים.")],
     "digital": {"level": "partial", "text": "אפשר לחשב מהמהדורות אילו פסוקים מסיימים פרשה פתוחה או סתומה, לספור ולהשוות בין מהדורות ולרשימת הרמב״ם (ראו לשונית פרשיות). אי אפשר לבדוק את צורת הריוח בכתב."}},
    {"id": "shirot", "title": "שירת הים והאזינו: אריח על גבי לבינה", "level": "מעכב",
     "summary": "שירת הים בשלשים שיטין, ראשונה כדרכה והשאר מתחלפות בין ריוח אחד באמצע לשני ריוחים. האזינו בשבעים שיטין, כל שיטה חלוקה לשתים. כתב שירה כשאר הכתב, או שאר הכתב כשירה: פסול.",
     "refs": [f"{_R} 8:4", f"{SA} 275:3", f"{SOF} 12:10"],
     "views": [V("רמב״ם", f"{_R} 7:11", "כתב השירה כשאר הכתב, או פרשה אחת כשירה: פסול."),
               V("שולחן ערוך", f"{SA} 275:3", "כתב השירה כשאר הכתב בלא פיזור: פסול; אם שינה בפיזור, לא פסל, ובלבד שיהא אריח על גבי לבינה."),
               V("שולחן ערוך", f"{SA} 275:4", "שירת הים בשלשים שיטות: ראשונה כדרכה, ושאר השיטות אחת ריוח אחד באמצע ואחת ריוח בשני מקומות, עד שהשיטה חלוקה לשלש ונמצא ריוח כנגד הכתב וכתב כנגד הריוח."),
               V("שולחן ערוך", f"{SA} 275:5", "שירת האזינו: כל שיטה חלוקה לשתים בריוח אחד באמצע, בשבעים שיטות."),
               V("ש״ך", f"{SHACH} 275:7:1", "״אריח על גבי לבינה״ נאמר בשירת הים; בשירת האזינו אין כותבים כך, אלא כל שיטה חלוקה לשתים."),
               V("ט״ז", f"{TAZ} 275:6", "אריח הוא הכתב (בשיעור ג׳ טפחים) ולבינה המקום הפנוי (טפח וחצי), והשיטה הנכתבת בשלשה מקומות יש לה שני מקומות פנוי."),
               V("גר״א", f"{GRA} 275:4", "״מסורג״ שבמסכת סופרים הוא שאין כתוב אריח על גבי לבינה."),
               V("מסכת סופרים", f"{SOF} 12:10", "ר׳ זעירא בשם רב: שירת הים ושירת דבורה נכתבות אריח על גבי לבינה ולבינה על גבי אריח."),
               V("מסכת סופרים", f"{SOF} 13:3", "עשרת בני המן ומלכי כנען: אריח על גבי אריח ולבינה על גבי לבינה."),
               V("קסת הסופר", f"{KS} 16:1", "שירת הים: שיטה פנויה לפניה ולאחריה, שני הריוחים ביחד כשיעור סתומה; חמש שיטין בראש הדף, ״וזהו רק למצוה ולא לעיכוב״.")],
     "digital": {"level": "partial", "text": "אפשר להציג את מבנה השיטין מנתוני הרמב״ם ומסכת סופרים על הטקסט שבספרייה (לשונית שירות). זו המחשה בלבד, ולא תיקון סופרים."}},
    {"id": "stitching", "title": "תפירה בגידי בהמה טהורה", "level": "מעכב",
     "summary": "תופרים את היריעות רק בגידי בהמה או חיה טהורה; הלכה למשה מסיני. תפרן שלא בגידין פסול עד שיתירה ויתפור כהלכה.",
     "refs": [f"{_R} 9:13", f"{SA} 278:1", f"{KS} 17:1"],
     "views": [V("רמב״ם", f"{_R} 9:13", "תפר שלא בגידין או בגידי בהמה טמאה: פסול עד שיתיר ויחזור ויתפור."),
               V("שולחן ערוך", f"{SA} 278:3", "נקרע רוב התפירה אבל עדיין מחוברות בחמש או שש תפירות של קיימא: כשר."),
               V("רמ״א (תרומת הדשן)", f"{SA} 278:2", "בשעת הדחק שאי אפשר בגידין: נתפרה במשי, קורין בה, ואם אפשר לתקן בגידין אין קורין עד שיתקן."),
               V("קסת הסופר", f"{KS} 17:1", "אין לקנות גידין מעכו״ם שמא מבהמה טמאה; ובגיד הנשה צריך עיון והנטייה להחמיר.")],
     "digital": {"level": "no", "text": "חומר התפירה אינו בטקסט."}},
    {"id": "magiah", "title": "הגהה: אסור להשהות ספר שאינו מוגה", "level": "מעכב",
     "summary": "ספר תורה שאינו מוגה אסור להשהותו יותר משלשים יום. בדף שיש בו שלש טעויות מתקנים, ארבע יגנז; מלא במקום חסר גרוע יותר מחסר במקום מלא (תלייה לעומת גרידה).",
     "refs": [f"{_R} 7:12", f"{SA} 279:1", f"{SA} 279:4"],
     "views": [V("רמב״ם", f"{_R} 7:13", "הטעם: מלא במקום חסר נתלה בין השיטין, וחסר במקום מלא נגרד, והגרידה אינה גנאי."),
               V("שולחן ערוך", f"{SA} 279:3", "נמצאו בו שלש טעויות: אסור לקרות בו עד שיגיהנו, כי הוא מוחזק במוטעה."),
               V("שולחן ערוך", f"{SA} 279:1", "אין להגיה על פי הסברא, כי אם בראיה ברורה שיש בו טעות."),
               V("רמ״א", f"{SA} 279:4", "כשגורד מרחיב מעט את האות שלפניו ושלאחריו, שלא יהיה מקום הגרד הפסק בתיבה."),
               V("קסת הסופר", f"{KS} 19:1", "מקור האיסור: ״אל תשכן באהליך עולה״."),
               V("טור", f"{TUR} 279:1", "אפילו קרא בו בדיעבד לא יצא כיון שהוא חסר או יתר אפילו אות אחת, וחוזר לראש הסדר.")],
     "digital": {"level": "yes", "text": "כאן כלי עזר דיגיטלי הוא הגיוני: השוואת התמלול לנוסחי ייחוס כדי להצביע על מקומות לבדיקה. ההכרעה והתיקון הם תמיד של מגיה אדם בקי."}},
    {"id": "genizah", "title": "כבוד, גניזה ומכירה", "level": "למצוה",
     "summary": "ספר תורה כשר נוהגים בו קדושה יתירה. בלה או נפסל: נגנז בכלי חרס אצל תלמידי חכמים. אסור למכרו אלא ללמוד תורה או לישא אשה.",
     "refs": [f"{_R} 10:2", f"{_R} 10:3", f"{SA} 282:10"],
     "views": [V("רמב״ם", f"{_R} 10:2", "אסור למכור אפילו אין לו מה יאכל, אלא ללמוד תורה או לישא אשה והוא שאין לו דבר אחר למכור."),
               V("רמ״א", f"{SA} 270:1", "הוא הדין לצורך פדיון שבויים.")],
     "digital": {"level": "no", "text": "עניין של הלכות כבוד ומעשה, לא של בדיקת טקסט."}},
]

# Which of Rambam's 20 invalidators (Tefillin 10:1) a computer can help with.
RAMBAM20_DIGITAL = {
    9: ("partial", "שפת הכתב והתמלול ניתנים לבדיקה, לא הכתב שעל הקלף."),
    12: ("yes", "השוואה לנוסח ייחוס (חסר)."), 13: ("yes", "השוואה לנוסח ייחוס (יתר)."),
    17: ("partial", "מקומות הפרשיות בנוסח כן; צורת הריוח לא."), 18: ("partial", "מבנה שיטי השירות המחשה בלבד."),
    19: ("partial", "מבנה שיטי השירות המחשה בלבד."),
}
_GEM = {"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9, "י": 10, "כ": 20}


def _gem(s: str) -> int:
    return sum(_GEM.get(c, 0) for c in s)


def parse_rambam20(text: str) -> list[dict]:
    """The twenty invalidators of Tefillin 10:1, parsed from the numbered list '(א) ...(ב) ...'."""
    t = clean_text(text)
    m = re.search(r"ואלו הן:?\s*(\(א\).*)$", t)
    if not m:
        return []
    items = []
    for im in re.finditer(r"\(([א-כ]{1,2})\)\s*(.*?)(?=\([א-כ]{1,2}\)|$)", m.group(1)):
        n = _gem(im.group(1))
        body = im.group(2).strip()
        tail = None
        if n == 20 and " ושאר הדברים" in body:
            body, tail = body.split(" ושאר הדברים", 1)
            tail = "ושאר הדברים" + tail
        lvl, why = RAMBAM20_DIGITAL.get(n, ("no", "עניין פיזי, כוונה או כתב יד, שאינם ניתנים לבדיקה על טקסט דיגיטלי."))
        items.append({"n": n, "text": body.strip(), "digital": {"level": lvl, "text": why}, **({"tail": tail} if tail else {})})
    return items


def laws_payload(con) -> dict:
    laws, missing = copy.deepcopy(LAWS), set()
    cache: dict[str, dict] = {}

    def info(ref: str) -> dict:
        if ref not in cache:
            t = get_text(con, ref)
            cache[ref] = {"ref": ref, "exists": t is not None, "excerpt": clean_text(t)[:240] if t else None}
            if t is None:
                missing.add(ref)
        return cache[ref]

    for law in laws:
        law["sources"] = [info(r) for r in law["refs"]]
        for v in law["views"]:
            v["exists"] = info(v["ref"])["exists"] if v.get("ref") else None
    t20 = get_text(con, f"{RAMBAM} 10:1")
    return {"disclaimer": DISCLAIMER, "laws": laws, "rambam_20": parse_rambam20(t20) if t20 else [],
            "missing_refs": sorted(missing), "all_refs_exist": not missing,
            "digital_levels": {"yes": "אפשר לבדוק (כעזר בלבד)", "partial": "חלקית", "no": "אי אפשר לבדוק דיגיטלית"},
            "note": ("הרשימה מסכמת את עיקרי ההלכות כפי שהן מופיעות במקורות שבספרייה ואינה פסק הלכה. "
                     "הדעות שהובאו הן קיצור של הטקסט בספרייה, ויש לעיין במקור (כל מקור מקושר).")}


# ---------------------------------------------------------------------------------------------------------------------
# 4. Shirat HaYam and Ha'azinu layout
# ---------------------------------------------------------------------------------------------------------------------
_DIVINE = re.compile(r"(?:יי|ה)['׳’]")
ILLUSTRATION = "המחשה, לא תיקון סופרים"

# Lines framing the songs (Rambam 7:10 / Rema 275:6 / Keset 16): first words of the lines above and below.
FRAME = {
    "yam": {"above": ["הבאים", "ביבשה", "ה׳", "מת", "במצרים"], "below": ["ותקח", "אחריה", "סוס", "ויצאו", "ויבאו"], "source": f"{_R} 7:10"},
    "haazinu": {"above": ["ואעידה", "אחרי", "הדרך", "באחרית", "להכעיסו", "קהל"], "below": ["ויבא", "לדבר", "אשר", "הזאת", "אשר"], "source": f"{_R} 7:10"},
}


def norm_opener(w: str) -> str:
    return "".join(_LETTER.findall(_DIVINE.sub("יהוה", w))).translate(_FIN)


def _skel(w: str) -> str:
    return re.sub("[יו]", "", w)


def align_openers(words: list[str], openers: list[list[str]], max_seg: int | None = None) -> dict | None:
    """Place the openers (each a list of words) in order on the word list so that the first opener is at word 0 and the
    mismatch cost is minimal; returns {'starts': [...], 'cost': x, 'mismatches': [k...]}."""
    N, K = len(words), len(openers)
    if not K or N < K:
        return None
    W = [w.translate(_FIN) for w in words]
    avg = N / K
    max_seg = max_seg or max(8, int(avg * 3) + 3)

    def wc(a, b, nxt=""):
        if a == b:
            return 0.0
        if nxt and a == b + nxt:           # an edition may split one word in two ('ה ליהוה' for 'הליהוה')
            return 0.2
        return 0.4 if _skel(a) == _skel(b) else 1.0

    cost = []
    for op in openers:
        opn = [o.translate(_FIN) for o in op]
        cost.append([sum(wc(o, W[p + j], W[p + j + 1] if p + j + 1 < N else "") if p + j < N else 1.0
                         for j, o in enumerate(opn)) / len(opn) for p in range(N)])
    INF = 1e18
    dp = [[INF] * N for _ in range(K)]
    back = [[-1] * N for _ in range(K)]
    dp[0][0] = cost[0][0]
    for k in range(1, K):
        prev = dp[k - 1]
        for p in range(k, N):
            best, bq = INF, -1
            for q in range(max(k - 1, p - max_seg), p):
                v = prev[q]
                if v >= INF:
                    continue
                v += 0.05 * abs(p - q - avg) / avg
                if v < best:
                    best, bq = v, q
            if bq >= 0:
                dp[k][p], back[k][p] = best + cost[k][p], bq
    cand = [(dp[K - 1][p] + 0.05 * abs(N - p - avg) / avg, p) for p in range(K - 1, N) if N - p <= max_seg and dp[K - 1][p] < INF]
    if not cand:
        return None
    _, p = min(cand)
    starts = [0] * K
    for k in range(K - 1, 0, -1):
        starts[k] = p
        p = back[k][p]
    starts[0] = 0
    return {"starts": starts, "cost": round(sum(cost[k][starts[k]] for k in range(K)), 3),
            "mismatches": [k for k in range(K) if cost[k][starts[k]] >= 0.5]}


def parse_soferim_list(text: str, intro: str) -> list[list[str]]:
    """Soferim 12:9 / 12:11 lines lists: '<intro>. a. b. c' (completions in parentheses are dropped)."""
    t = clean_text(text)
    i = t.find(intro)
    t = t[i + len(intro):] if i >= 0 else t
    t = re.sub(r"\([^)]*\)", "", t).replace("[", "").replace("]", "")
    out = []
    for item in re.split(r"[.:]", t):
        ws = [norm_opener(w) for w in item.split()]
        ws = [w for w in ws if w]
        if ws:
            out.append(ws)
    return out


def parse_rambam_shirot(text: str) -> dict:
    """The two 70-word lists for Ha'azinu (first word of each line, first word of each second half) and the Shirat HaYam
    line count, from Rambam 8:4."""
    t = clean_text(text)
    res = {"haazinu": None, "yam": None}
    a = t.find("ואלו הן התיבות שבראש כל שיטה ושיטה")
    b = t.find("כל אלו התיבות שבראש", a)
    c = t.find("שבראש כל חצי שיטה", b)
    d = t.find("שירת הים כותבין", c)
    if min(a, b, c, d) >= 0:
        right = [w.strip(":") for w in t[a:b].split(":", 1)[1].split()]
        left = [w.strip(":") for w in t[c:d].split(":", 1)[1].split()]
        res["haazinu"] = {"lines": len(right), "right": right, "left": left}
    m = re.search(r"שירת הים כותבין אותה ב(\S+) שיטות", t)
    if m:
        res["yam"] = {"lines": heb_number(m.group(1)), "text": t[t.find("שירת הים כותבין"):].split(":", 1)[0]}
    return res


def _verse_words(con, vid: int, book: str, chapter: int, v1: int, v2: int) -> tuple[list[str], list[tuple[int, str]]]:
    words, starts = [], []
    for v in range(v1, v2 + 1):
        r = con.execute("SELECT text FROM segments WHERE version_id=? AND ref=?", (vid, f"{book} {chapter}:{v}")).fetchone()
        if not r:
            continue
        ws = words_of(r[0])
        starts.append((len(words), f"{book} {chapter}:{v}"))
        words += ws
    return words, starts


def _pick_version(con, title: str) -> tuple[int, str] | None:
    for vt in (MASORAH, "Tanach with Text Only", LENINGRAD, "Tanach with Nikkud"):
        r = con.execute("SELECT id, version_title FROM versions WHERE title=? AND version_title=? AND language='he'", (title, vt)).fetchone()
        if r:
            return r[0], r[1]
    return None


def split_by_weight(ws: list[str], weights: list[float]) -> list[list[str]]:
    """Cut the word list into len(weights) non-empty parts, letters proportional to weights (as far as possible)."""
    n = len(weights)
    if n == 1 or len(ws) < n:
        return [ws]
    lens = [len(w) + 1 for w in ws]
    tot, cum, cuts, acc = sum(lens), 0, [], 0.0
    for i, wt in enumerate(weights[:-1]):
        acc += wt / sum(weights) * tot
        best = None
        for j in range((cuts[-1] + 1) if cuts else 1, len(ws) - (n - 1 - i) + 1):
            if best is None or abs(sum(lens[:j]) - acc) < abs(sum(lens[:best]) - acc):
                best = j
        cuts.append(best)
    parts, prev = [], 0
    for cpos in cuts + [len(ws)]:
        parts.append(ws[prev:cpos])
        prev = cpos
    return parts


def _line_marks(starts_by_word: dict[int, str], lo: int, hi: int) -> list[dict]:
    return [{"i": i - lo, "ref": ref} for i, ref in sorted(starts_by_word.items()) if lo <= i < hi]


def compute_shirot(con) -> dict:
    out = {"disclaimer": DISCLAIMER, "illustration": ILLUSTRATION, "yam": None, "haazinu": None, "frame": FRAME}
    ram_text = get_text(con, SECTIONS_REF)
    ram = parse_rambam_shirot(clean_text(ram_text)) if ram_text else {"haazinu": None, "yam": None}
    # --- Shirat HaYam: Exodus 15:1-19, 30 lines, openers from Soferim 12:11
    pv = _pick_version(con, "Exodus")
    sof = get_text(con, f"{SOF} 12:11")
    if pv and sof:
        words, vstarts = _verse_words(con, pv[0], "Exodus", 15, 1, 19)
        openers = parse_soferim_list(sof, "שלשים שיטין")
        want = (ram.get("yam") or {}).get("lines") or 30
        opener_note = None
        multi = [i for i, o in enumerate(openers) if len(o) > 1]
        if len(openers) < want and len(multi) >= want - len(openers):
            # an item with two words (here "אויב נפשי") is two openers written without a period between them
            for i in reversed(multi[:want - len(openers)]):
                opener_note = f"הפתיחה ״{' '.join(openers[i])}״ פוצלה לשתי שיטות, כדי להגיע למנין {want} השיטין שמונה הרמב״ם (במקור אין נקודה ביניהן)."
                openers[i:i + 1] = [[w] for w in openers[i]]
        al = align_openers(words, openers)
        if al and words:
            st = al["starts"]
            vmap = {i: ref for i, ref in vstarts}
            lines = []
            for k in range(len(st)):
                lo, hi = st[k], st[k + 1] if k + 1 < len(st) else len(words)
                n = k + 1
                gaps = 0 if n == 1 else (1 if n % 2 == 0 else 2)
                parts = split_by_weight(words[lo:hi], [44, 44] if gaps == 1 else [27, 34, 27] if gaps == 2 else [1])
                gaps = len(parts) - 1 if gaps and len(parts) - 1 != gaps and len(parts) > 1 else (gaps if len(parts) > 1 else 0)
                segs, off = [], lo
                for p in parts:
                    segs.append({"words": p, "marks": _line_marks(vmap, off, off + len(p))})
                    off += len(p)
                lines.append({"n": n, "gaps": gaps, "opener": " ".join(openers[k]), "opener_match": k not in al["mismatches"], "segments": segs})
            out["yam"] = {"title": "שירת הים", "range": "Exodus 15:1-19", "form": "אריח על גבי לבינה", "version": pv[1],
                          "lines": lines, "line_count": len(lines), "words": len(words),
                          "stated_lines": (ram.get("yam") or {}).get("lines"),
                          "openers_source": f"{SOF} 12:11", "openers_note": opener_note, "rule_sources": [f"{_R} 8:4", f"{SOF} 12:10", f"{SA} 275:4", f"{KS} 16:1"],
                          "alignment": {"cost": al["cost"], "mismatched_openers": [k + 1 for k in al["mismatches"]]},
                          "gap_rule": ("שיטה ראשונה כדרכה; אחריה מתחלפות שיטה עם ריוח אחד באמצע ושיטה עם שני ריוחים (כסדר הרמב״ם ח:ד). "
                                       "מקום הריוחים בתוך השיטה משוער לפי מנין האותיות; רק תחילת כל שיטה לקוחה ממסכת סופרים."),
                          "note": ILLUSTRATION}
    # --- Ha'azinu: Deuteronomy 32:1-43, 70 lines x 2 halves, openers from Rambam 8:4
    pv = _pick_version(con, "Deuteronomy")
    hz = ram.get("haazinu")
    if pv and hz and hz["lines"] and len(hz["left"]) == hz["lines"]:
        words, vstarts = _verse_words(con, pv[0], "Deuteronomy", 32, 1, 43)
        seq = []
        for r_, l_ in zip(hz["right"], hz["left"]):
            seq += [[norm_opener(r_)], [norm_opener(l_)]]
        al = align_openers(words, seq)
        if al and words:
            st = al["starts"]
            vmap = {i: ref for i, ref in vstarts}
            ends = st[1:] + [len(words)]
            lines = []
            for k in range(hz["lines"]):
                halves = []
                for h in (2 * k, 2 * k + 1):
                    halves.append({"words": words[st[h]:ends[h]], "marks": _line_marks(vmap, st[h], ends[h])})
                lines.append({"n": k + 1, "opener": hz["right"][k], "opener_left": hz["left"][k], "segments": halves, "gaps": 1,
                              "opener_match": 2 * k not in al["mismatches"] and 2 * k + 1 not in al["mismatches"]})
            sof9 = get_text(con, f"{SOF} 12:9")
            agree = None
            if sof9:
                sl = [x[0] for x in parse_soferim_list(sof9, "וסימן תחלת השיטים") if x]
                rl = [norm_opener(x) for x in hz["right"]]
                agree = {"soferim_openers": len(sl), "rambam_openers": len(rl),
                         "matching_blocks_words": sum(b.size for b in SequenceMatcher(None, rl, sl, autojunk=False).get_matching_blocks())}
            out["haazinu"] = {"title": "האזינו", "range": "Deuteronomy 32:1-43", "form": "אריח על גבי אריח", "version": pv[1],
                              "lines": lines, "line_count": len(lines), "words": len(words), "stated_lines": hz["lines"],
                              "openers_source": SECTIONS_REF, "rule_sources": [f"{_R} 8:4", f"{SA} 275:5", f"{KS} 16:2", f"{SOF} 12:9"],
                              "soferim_vs_rambam": agree,
                              "alignment": {"cost": al["cost"], "mismatched_openers": [k + 1 for k in al["mismatches"]]},
                              "gap_rule": "כל שיטה חלוקה לשתים בריוח אחד באמצע (שיעור סתומה), והריוחים זה על גבי זה. פתיחות כל שיטה וכל חצי שיטה לקוחות מרשימת הרמב״ם.",
                              "note": ILLUSTRATION}
    out["available"] = bool(out["yam"] or out["haazinu"])
    return out


# ---------------------------------------------------------------------------------------------------------------------
# cache + router
# ---------------------------------------------------------------------------------------------------------------------
def _ensure(con):
    con.execute("CREATE TABLE IF NOT EXISTS sofrut_cache (name TEXT PRIMARY KEY, sig TEXT NOT NULL, computed_at TEXT NOT NULL, payload TEXT NOT NULL)")


def _sig(con, titles: list[str]) -> str:
    ph = ",".join("?" * len(titles))
    rows = con.execute(f"SELECT id, imported_at FROM versions WHERE title IN ({ph}) AND language='he' ORDER BY id", titles).fetchall()
    return hashlib.sha256((f"v{CODE_VERSION}|" + "|".join(f"{r[0]}:{r[1]}" for r in rows)).encode()).hexdigest()


def cached(con, name: str, titles: list[str], compute, refresh: bool = False) -> dict:
    """Cache heavy results in sofrut_cache, keyed by the ids/import times of the versions they depend on.
    A read-only connection simply computes every time."""
    sig = _sig(con, titles)
    try:
        _ensure(con)
        if not refresh:
            r = con.execute("SELECT payload, computed_at FROM sofrut_cache WHERE name=? AND sig=?", (name, sig)).fetchone()
            if r:
                return json.loads(r[0]) | {"cached": True, "computed_at": r[1]}
    except sqlite3.Error:
        pass
    data, ts = compute(), now()
    try:
        con.execute("INSERT OR REPLACE INTO sofrut_cache(name, sig, computed_at, payload) VALUES (?,?,?,?)",
                    (name, sig, ts, json.dumps(data, ensure_ascii=False)))
        con.commit()
    except sqlite3.Error:
        pass
    return data | {"cached": False, "computed_at": ts}


def make_router(node) -> APIRouter:
    r = APIRouter()
    _ensure(node.con)

    @r.get("/api/sofrut")
    def overview():
        con = node.con
        have = {k: len(_find_vids(con, vt)) for k, vt in VERSIONS.items()}
        return {"disclaimer": DISCLAIMER, "editions": have, "rambam_sections_ref": SECTIONS_REF,
                "rambam_sections_present": get_text(con, SECTIONS_REF) is not None,
                "endpoints": ["/api/sofrut/parashiyot", "/api/sofrut/parashiyot/breaks?version=masorah&book=Genesis",
                              "/api/sofrut/rambam-sections", "/api/sofrut/laws", "/api/sofrut/shirot"]}

    @r.get("/api/sofrut/parashiyot")
    def parashiyot(refresh: bool = False):
        return cached(node.con, "parashiyot", BOOKS + [RAMBAM], lambda: compute_parashiyot(node.con), refresh)

    @r.get("/api/sofrut/parashiyot/breaks")
    def breaks(version: str, book: str):
        if version not in VERSIONS or book not in BOOKS:
            raise HTTPException(400, "version must be masorah|leningrad and book one of the five books")
        vid = _find_vids(node.con, VERSIONS[version]).get(book)
        if vid is None:
            raise HTTPException(404, "version not in the library")
        verses, br = book_breaks(node.con, vid)
        return {"version": version, "version_title": VERSIONS[version], "book": book, "verses": verses, **_summ(br), "breaks": br}

    @r.get("/api/sofrut/rambam-sections")
    def rambam(refresh: bool = False):
        return cached(node.con, "rambam", [RAMBAM], lambda: rambam_sections(node.con), refresh)

    @r.get("/api/sofrut/laws")
    def laws():
        return laws_payload(node.con)

    @r.get("/api/sofrut/shirot")
    def shirot(refresh: bool = False):
        return cached(node.con, "shirot", ["Exodus", "Deuteronomy", RAMBAM, SOF], lambda: compute_shirot(node.con), refresh)

    return r
