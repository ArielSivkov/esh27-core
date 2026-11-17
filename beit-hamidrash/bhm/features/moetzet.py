"""מועצת חכמים: research summary of sources and Gedolei Yisrael on each part of the project.

The data (moetzet_data/moetzet.json) was produced by 10 research agents and
checked by 10 adversarial verifiers: each classical citation was compared
with the text in the local library, and each contemporary claim with a web
source. Every position carries its verdict. This is a summary for rabbis,
not a halachic ruling.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

DATA = Path(__file__).resolve().parent / "moetzet_data" / "moetzet.json"
NAV = {"label": "מועצת חכמים", "href": "#/moetzet"}
NOTICE = "סיכום מקורות לעיון רבנים בלבד. אינו פסק הלכה. ההשלכות למערכת הן הסקה שלנו וטעונות הכרעת רבני הפרויקט."


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def make_router(node) -> APIRouter:
    r = APIRouter()

    @r.get("/api/moetzet")
    def index():
        d = load()
        return {"notice": NOTICE, "totals": d.get("totals", {}),
                "topics": [{"key": t["key"], "title": t["title"], "summary": t["summary"],
                            "positions": len(t["positions"]),
                            "verified": sum(1 for p in t["positions"] if p.get("verdict") == "verified")}
                           for t in d["topics"]]}

    @r.get("/api/moetzet/{key}")
    def topic(key: str):
        for t in load()["topics"]:
            if t["key"] == key:
                return {"notice": NOTICE, **t}
        raise HTTPException(404, "no such topic")

    return r
