"""Hebrew table of contents: Sefaria TOC metadata (cached) restricted to books we hold."""
from __future__ import annotations

import json
import time
import urllib.request

from fastapi import APIRouter, HTTPException, Request

NAV = {"label": "תוכן עניינים", "href": "#/toc"}
TOC_URL = "https://storage.googleapis.com/sefaria-export/table_of_contents.json"
MAX_BYTES = 40_000_000

# Built-in Hebrew names of top categories (used offline / when the cache lacks them).
HE_TOP = {
    "Tanakh": "תנ\"ך", "Mishnah": "משנה", "Talmud": "תלמוד", "Midrash": "מדרש",
    "Halakhah": "הלכה", "Kabbalah": "קבלה", "Liturgy": "תפילה", "Jewish Thought": "מחשבת ישראל",
    "Tosefta": "תוספתא", "Chasidut": "חסידות", "Musar": "מוסר", "Responsa": "שו\"ת",
    "Second Temple": "בית שני", "Reference": "ספרי עיון", "Philosophy": "פילוסופיה",
    "Modern Works": "ספרות מודרנית", "Apocrypha": "ספרים חיצוניים", "Targum": "תרגום",
    "Torah": "תורה", "Prophets": "נביאים", "Writings": "כתובים", "Bavli": "תלמוד בבלי",
    "Yerushalmi": "תלמוד ירושלמי", "Seder Zeraim": "סדר זרעים", "Seder Moed": "סדר מועד",
    "Seder Nashim": "סדר נשים", "Seder Nezikin": "סדר נזיקין", "Seder Kodashim": "סדר קדשים",
    "Seder Tahorot": "סדר טהרות", "Rishonim on Tanakh": "ראשונים על התנ\"ך",
    "Acharonim on Tanakh": "אחרונים על התנ\"ך", "Commentary": "פרשנות", "Other": "אחר",
}
OTHER = "Other"
LOCAL_HOSTS = ("127.0.0.1", "::1", "testclient")
REFRESH_MIN_INTERVAL = 600
_last_refresh: dict = {}


def _cache_path(node):
    return node.home / "toc_cache.json"


def fetch_toc(node, url: str | None = None) -> list:
    """Download the Sefaria TOC into the node cache and return it."""
    req = urllib.request.Request(url or TOC_URL, headers={"User-Agent": "bhm-toc"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("toc too large")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("unexpected toc format")
    _cache_path(node).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def load_cache(node) -> list | None:
    try:
        data = json.loads(_cache_path(node).read_text(encoding="utf-8"))
        return data if isinstance(data, list) else None
    except (OSError, ValueError):
        return None


def library_books(con) -> dict:
    books: dict = {}
    for r in con.execute("SELECT title, he_title, categories FROM versions ORDER BY id"):
        try:
            cats = json.loads(r["categories"] or "[]")
        except ValueError:
            cats = []
        b = books.setdefault(r["title"], {"title": r["title"], "he_title": r["he_title"], "categories": cats})
        if not b["he_title"] and r["he_title"]:
            b["he_title"] = r["he_title"]
    return books


def _book(b, he=None):
    return {"title": b["title"], "he_title": he or b.get("he_title") or b["title"]}


def _prune(nodes, books, used):
    out = []
    for n in nodes if isinstance(nodes, list) else []:
        if not isinstance(n, dict):
            continue
        if isinstance(n.get("contents"), list):
            kids = _prune(n["contents"], books, used)
            if kids:
                en = str(n.get("category") or n.get("title") or "")
                out.append({"category": en, "he": str(n.get("heCategory") or HE_TOP.get(en) or en), "children": kids})
        elif n.get("title") in books:
            used.add(n["title"])
            out.append({"book": _book(books[n["title"]], n.get("heTitle"))})
    return out


def _fallback(books):
    root: dict = {}
    for b in sorted(books.values(), key=lambda b: b["title"]):
        cur = root
        for c in (b["categories"] or [OTHER]):
            cur = cur.setdefault(c, {"__books": []})
        cur["__books"].append(_book(b))

    def conv(d):
        kids = [{"category": k, "he": HE_TOP.get(k) or k, "children": conv(v)}
                for k, v in d.items() if k != "__books"]
        return kids + [{"book": x} for x in d.get("__books", [])]
    return conv(root)


def build_tree(books: dict, toc: list | None):
    if not toc:
        return _fallback(books), "fallback"
    used: set = set()
    tree = _prune(toc, books, used)
    rest = {t: b for t, b in books.items() if t not in used}
    if rest:  # books absent from the (possibly stale) TOC still appear
        tree.extend(_fallback(rest))
    return tree, "cache"


def _count(tree):
    return sum(1 if "book" in n else _count(n["children"]) for n in tree)


def _age(node):
    try:
        return int(time.time() - _cache_path(node).stat().st_mtime)
    except OSError:
        return None


def make_router(node) -> APIRouter:
    r = APIRouter()

    @r.get("/api/toc")
    def toc():
        warning = None
        data = load_cache(node)
        tree, source = build_tree(library_books(node.con), data)
        return {"source": source, "books": _count(tree), "tree": tree, "warning": warning,
                "note": "מבנה הקטגוריות מבוסס על מטא-דאטה של ספריא; מוצגים רק ספרים שבספרייה שלנו.",
                "cache_age_s": _age(node)}

    @r.post("/api/toc/refresh")
    def refresh(request: Request):
        if not request.client or request.client.host not in LOCAL_HOSTS:
            raise HTTPException(403, "local requests only")
        now = time.monotonic()
        last = _last_refresh.get(str(node.home))
        if last is not None and now - last < REFRESH_MIN_INTERVAL:
            raise HTTPException(429, "refresh rate limited")
        _last_refresh[str(node.home)] = now
        try:
            data = fetch_toc(node)
        except Exception as e:
            raise HTTPException(502, f"fetch failed: {type(e).__name__}")
        return {"ok": True, "top_categories": len(data)}

    return r
