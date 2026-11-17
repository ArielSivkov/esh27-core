"""sources_ai: local source finder (מאתר מקורות).

Retrieves passages for a question (search_fts if present, else LIKE over segments).
Optionally (env OLLAMA_URL) asks a local model to SUMMARIZE the retrieved sources only.
No network calls unless OLLAMA_URL is set. Never produces a summary without sources.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

NAV = {"label": "מאתר מקורות", "href": "#/sources_ai"}
LABEL = "סיכום ממוחשב, אינו פסק"
DISCLAIMER = "המאתר מחפש מקורות בלבד ואינו פוסק הלכה. לשאלה הלכתית יש לפנות לרב או לבית הדין."

_NIQQUD = re.compile(r"[֑-ׇ]")
_WORD = re.compile(r"[א-ת]+|[A-Za-z]{2,}")
_STOP = set("של על את אם או גם כי לא מה מי איך למה האם הוא היא הם הן זה זו זאת אשר כל אל עם בין עד לפי כמו יש אין הנה אבל".split())
MAX_Q = 500


class AskIn(BaseModel):
    question: str


def normalize(s: str) -> str:
    return _NIQQUD.sub("", s or "").replace("־", " ").replace("׳", "").replace("״", "")


def terms_of(q: str) -> list[str]:
    seen, out = set(), []
    for w in _WORD.findall(normalize(q)):
        if len(w) < 2 or w in _STOP or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out[:8]


def _has_table(con, name: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() is not None


def _candidates(con, terms: list[str], limit: int = 300) -> list[dict]:
    if _has_table(con, "search_fts"):
        try:
            q = " OR ".join('"%s"' % t.replace('"', "") for t in terms)
            rows = con.execute("SELECT ref, text FROM search_fts WHERE search_fts MATCH ? LIMIT ?", (q, limit)).fetchall()
            if rows:
                return [{"ref": r[0], "text": r[1], "version_title": ""} for r in rows]
        except Exception:
            pass  # unknown FTS schema: fall back to LIKE
    cond = " OR ".join("s.text LIKE ?" for _ in terms)
    rows = con.execute(
        f"SELECT s.ref, s.text, v.version_title FROM segments s JOIN versions v ON v.id=s.version_id WHERE {cond} LIMIT ?",
        [f"%{t}%" for t in terms] + [limit]).fetchall()
    return [{"ref": r[0], "text": r[1], "version_title": r[2]} for r in rows]


def rank(cands: list[dict], terms: list[str], top: int = 8) -> list[dict]:
    df = {t: sum(1 for c in cands if t in normalize(c["text"])) or 1 for t in terms}
    scored, seen = [], set()
    for c in cands:
        n = normalize(c["text"])
        hit = [t for t in terms if t in n]
        if not hit:
            continue
        score = sum(1.0 / df[t] ** 0.5 + 0.1 * len(t) for t in hit) * (1 + len(hit)) / (1 + len(n) / 800)
        key = (c["ref"], n[:60])
        if key in seen:
            continue
        seen.add(key)
        scored.append((score, c, hit))
    scored.sort(key=lambda x: -x[0])
    return [{"ref": c["ref"], "text": c["text"][:700], "version_title": c.get("version_title", ""),
             "score": round(s, 3), "matched": h} for s, c, h in scored[:top]]


def _call_model(url: str, model: str, prompt: str) -> str:
    req = urllib.request.Request(url.rstrip("/") + "/api/generate",
                                 data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode()).get("response", "")


def _prompt(question: str, sources: list[dict]) -> str:
    srcs = "\n".join(f"[{s['ref']}] {s['text']}" for s in sources)
    return ("סכם בקצרה ובעברית אך ורק מה שהמקורות שלהלן אומרים, וציין את המראה מקום בסוגריים מרובעים אחרי כל טענה. "
            "אל תוסיף מידע שאינו במקורות. אל תפסוק הלכה ואל תכריע; אם המקורות אינם עונים, אמור זאת.\n\n"
            f"שאלה: {question}\n\nמקורות:\n{srcs}\n\nסיכום:")


def make_router(node) -> APIRouter:
    r = APIRouter()
    node.con.execute("""CREATE TABLE IF NOT EXISTS sources_ai_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, qlen INTEGER NOT NULL,
        n_sources INTEGER NOT NULL, summarized INTEGER NOT NULL)""")
    node.con.commit()

    @r.post("/api/sources_ai/ask")
    def ask(body: AskIn):
        q = body.question.strip()
        if len(q) < 2 or len(q) > MAX_Q:
            raise HTTPException(400, "שאלה קצרה או ארוכה מדי")
        terms = terms_of(q)
        sources = rank(_candidates(node.con, terms), terms) if terms else []
        summary, model_err, used = None, None, False
        url = os.environ.get("OLLAMA_URL")
        if url and sources:  # never summarize without sources
            model = os.environ.get("OLLAMA_MODEL", "dictalm")
            try:
                text = _call_model(url, model, _prompt(q, sources)).strip()
                if text:
                    summary = {"label": LABEL, "ai_generated": True, "model": model, "text": text}
                    used = True
            except Exception as e:  # model is optional; sources still returned
                model_err = f"המודל המקומי אינו זמין ({type(e).__name__})"
        node.con.execute("INSERT INTO sources_ai_log(ts,qlen,n_sources,summarized) VALUES (?,?,?,?)",
                         (time.time(), len(q), len(sources), int(used)))
        node.con.commit()
        return {"question": q, "terms": terms, "sources": sources, "summary": summary,
                "model_enabled": bool(url), "model_error": model_err, "disclaimer": DISCLAIMER}

    @r.get("/api/sources_ai/status")
    def status():
        return {"model_enabled": bool(os.environ.get("OLLAMA_URL")),
                "fts": _has_table(node.con, "search_fts"), "disclaimer": DISCLAIMER}

    return r
