"""Articles with sources and edits: /api/articles.

An article is a ledger event of kind 'article'. An 'edit' event whose target is the
article id and whose author is the SAME author replaces title/text (latest wins);
edits by anyone else are ignored. Source references found in the text (English
"Genesis 1:1" or Hebrew "בראשית א:א") are resolved against the library.
No own tables are needed: everything is derived from the signed ledger.
"""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, HTTPException

from .. import ledger

NAME = "articles"
NAV = {"label": "מאמרים", "href": "#/articles"}

SNIPPET_LEN = 240
MAX_REFS = 100

# ---------------------------------------------------------------- Hebrew numerals
_GEM = {}
for _i, _c in enumerate("אבגדהוזחט", 1):
    _GEM[_c] = _i
for _i, _c in enumerate("יכלמנסעפצ", 1):
    _GEM[_c] = _i * 10
for _i, _c in enumerate("קרשת", 1):
    _GEM[_c] = _i * 100
_GEM.update({"ך": 20, "ם": 40, "ן": 50, "ף": 80, "ץ": 90})


def gematria(s: str) -> int | None:
    """Value of a Hebrew numeral word (<= 4 letters), else None."""
    if not s or len(s) > 4 or any(c not in _GEM for c in s):
        return None
    v = sum(_GEM[c] for c in s)
    return v if v > 0 else None


_NIQQUD = re.compile(r"[֑-ׇ]")


def _norm_he(s: str) -> str:
    s = _NIQQUD.sub("", unicodedata.normalize("NFC", s))
    return re.sub(r"[\"'׳״“”’\-־]", "", s).strip()


# ---------------------------------------------------------------- resolving
EN_CAND = re.compile(
    r"(?<![A-Za-z])((?:[1-3] )?[A-Z][A-Za-z'’\-]*(?: (?:of |on |ha |de |ben |bar )?[A-Z][A-Za-z'’\-]*)*) "
    r"(\d{1,3}[ab]?(?::\d{1,3})?)(?![\w:])")


class Resolver:
    def __init__(self, con):
        self.con = con
        self._he = None
        self._cache = {}

    def he_map(self) -> dict[str, str]:
        if self._he is None:
            m = {}
            for r in self.con.execute("SELECT DISTINCT title, he_title FROM versions WHERE he_title IS NOT NULL"):
                m.setdefault(_norm_he(r["he_title"]), r["title"])
            self._he = m
        return self._he

    def lookup(self, ref: str):
        """Return info for an existing ref (or the first segment under it)."""
        if ref in self._cache:
            return self._cache[ref]
        res = None
        for lo, hi in ((ref, ref + "\0"), (ref + ":", ref + ";")):
            row = self.con.execute(
                "SELECT s.ref, s.text, v.version_title, v.language FROM segments s JOIN versions v ON v.id=s.version_id "
                "WHERE s.ref >= ? AND s.ref < ? ORDER BY (v.language='he') DESC, s.seq LIMIT 1", (lo, hi)).fetchone()
            if row:
                t = row["text"]
                res = {"ref": ref, "segment_ref": row["ref"],
                       "snippet": t[:SNIPPET_LEN] + ("…" if len(t) > SNIPPET_LEN else ""),
                       "version_title": row["version_title"], "language": row["language"]}
                break
        self._cache[ref] = res
        return res

    def find(self, text: str) -> list[dict]:
        found, taken = [], []

        def add(start, end, shown, ref):
            if any(start < e and s < end for s, e in taken):
                return False
            hit = self.lookup(ref)
            if not hit:
                return False
            taken.append((start, end))
            found.append({**hit, "start": start, "end": end, "match": shown})
            return True

        # English: try dropping leading capitalised words ("See Genesis 1:1")
        for m in EN_CAND.finditer(text):
            words, num = m.group(1).split(" "), m.group(2)
            for i in range(len(words)):
                name = " ".join(words[i:])
                start = m.start(1) + (len(" ".join(words[:i])) + 1 if i else 0)
                if add(start, m.end(2), text[start:m.end(2)], f"{name} {num}"):
                    break
        # Hebrew
        hemap = self.he_map()
        toks = [(t.start(), t.end(), t.group()) for t in re.finditer(r"\S+", text)]
        i = 0
        while hemap and i < len(toks):
            hit = False
            for n in (4, 3, 2, 1):
                if i + n >= len(toks):
                    continue
                name = _norm_he(" ".join(t[2] for t in toks[i:i + n]).rstrip(",.;:"))
                title = hemap.get(name)
                if not title:
                    continue
                for ref, used in self._he_numbers(title, toks, i + n):
                    end = toks[i + n + used - 1][1]
                    if add(toks[i][0], end, text[toks[i][0]:end].rstrip(",;"), ref):
                        i += n + used - 1
                        hit = True
                        break
                if hit:
                    break
            i += 1
        found.sort(key=lambda f: f["start"])
        return found[:MAX_REFS]

    @staticmethod
    def _he_numbers(title, toks, j):
        """Candidate (ref, tokens_used) after a Hebrew book name, most specific first."""
        raw = toks[j][2]
        trail = raw[-1] if raw[-1] in ".:" else ""
        w = _norm_he(raw.rstrip(".,;"))
        m = re.fullmatch(r"([א-ת]{1,4})[:׃]([א-ת]{1,4})", w)
        if m:
            c, v = gematria(m.group(1)), gematria(m.group(2))
            if c and v:
                yield f"{title} {c}:{v}", 1
            return
        c = gematria(w.rstrip(":׃"))
        if not c:
            return
        if j + 1 < len(toks):
            nxt = _norm_he(toks[j + 1][2].rstrip(".,;:"))
            if nxt in ("עא", "עב"):
                yield f"{title} {c}{'a' if nxt == 'עא' else 'b'}", 2
        if trail == ".":
            yield f"{title} {c}a", 1
        elif trail == ":":
            yield f"{title} {c}b", 1
        yield f"{title} {c}", 1


# ---------------------------------------------------------------- articles
def _latest(con, art_events, hidden):
    """Map article id -> (title, text, same-author edit events, ignored count)."""
    ids = [a["id"] for a in art_events]
    edits = {i: [] for i in ids}
    ignored = {i: 0 for i in ids}
    author = {a["id"]: a["author"] for a in art_events}
    for k in range(0, len(ids), 500):
        chunk = ids[k:k + 500]
        q = ",".join("?" * len(chunk))
        for r in con.execute(f"SELECT * FROM events WHERE kind='edit' AND target IN ({q}) ORDER BY ts, id", chunk):
            e = ledger.row_to_event(r)
            if e["id"] in hidden:
                continue
            if e["author"] == author[e["target"]]:
                edits[e["target"]].append(e)
            else:
                ignored[e["target"]] += 1
    out = {}
    for a in art_events:
        title, text = str(a["body"].get("title", "")), str(a["body"].get("text", ""))
        for e in edits[a["id"]]:
            title = str(e["body"].get("title") or title)
            text = str(e["body"].get("text") or text)
        out[a["id"]] = (title, text, edits[a["id"]], ignored[a["id"]])
    return out


def make_router(node):
    router = APIRouter()

    class _Con:  # resolves to the calling thread's connection
        def __getattr__(self, k):
            return getattr(node.con, k)
    con = _Con()

    def _article_events(one=None):
        H = ledger.hidden(con)
        if one:
            rows = con.execute("SELECT * FROM events WHERE kind='article' AND id=?", (one,))
        else:
            rows = con.execute("SELECT * FROM events WHERE kind='article' ORDER BY ts DESC, id DESC")
        return [ledger.row_to_event(r) for r in rows if r["id"] not in H], H

    @router.get("/api/articles")
    def list_articles(limit: int = 50):
        limit = max(1, min(limit, 500))
        evs, H = _article_events()
        evs = evs[:limit]
        N, latest = ledger.names(con), _latest(con, evs, H)
        out = []
        for a in evs:
            title, text, edits, _ = latest[a["id"]]
            out.append({"id": a["id"], "title": title, "author": a["author"],
                        "author_name": N.get(a["author"], a["author"][:10]), "ts": a["ts"],
                        "edited": bool(edits), "updated": edits[-1]["ts"] if edits else a["ts"],
                        "snippet": text[:200] + ("…" if len(text) > 200 else "")})
        return out

    @router.get("/api/articles/{article_id}")
    def get_article(article_id: str):
        evs, H = _article_events(article_id)
        if not evs:
            raise HTTPException(404, "no such article")
        a = evs[0]
        N, R = ledger.names(con), ledger.roles(con)
        title, text, edits, ignored = _latest(con, evs, H)[a["id"]]
        history = [{"id": a["id"], "kind": "article", "ts": a["ts"], "title": a["body"].get("title", ""),
                    "text": a["body"].get("text", "")}]
        history += [{"id": e["id"], "kind": "edit", "ts": e["ts"], "title": e["body"].get("title") or "",
                     "text": e["body"].get("text", "")} for e in edits]
        return {"id": a["id"], "title": title, "text": text, "author": a["author"],
                "author_name": N.get(a["author"], a["author"][:10]),
                "author_roles": sorted(R.get(a["author"], set())),
                "ts": a["ts"], "updated": edits[-1]["ts"] if edits else a["ts"],
                "history": history, "ignored_edits": ignored,
                "refs": Resolver(con).find(text)}

    return router
