"""HTTP API and web UI for a node. Run: python -m bhm serve"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import beitdin, ledger, library
from .ledger import LedgerError
from .node import Node

WEB = Path(__file__).resolve().parent.parent / "web"


class PostIn(BaseModel):
    user: str
    kind: str
    body: dict
    ref: str | None = None
    target: str | None = None


def create_app(node: Node | None = None) -> FastAPI:
    node = node or Node()

    class _Con:  # resolves to the calling thread's connection
        def __getattr__(self, k):
            return getattr(node.con, k)
    con = _Con()
    app = FastAPI(title="בית המדרש הגדול · ESH27", docs_url="/api/docs")

    def decorate(evs):
        R, N, H = ledger.roles(con), ledger.names(con), ledger.hidden(con)
        ends = {}
        for r in con.execute("SELECT target, author FROM events WHERE kind='endorse'"):
            ends.setdefault(r["target"], set()).add(r["author"])
        out = []
        for e in evs:
            if e["id"] in H:
                continue
            en = ends.get(e["id"], set())
            out.append({**e, "author_name": N.get(e["author"], e["author"][:10]),
                        "author_roles": sorted(R.get(e["author"], set())),
                        "endorsements": len(en),
                        "scholar_endorsements": sum(1 for a in en if "talmid_chacham" in R.get(a, set()))})
        return out

    @app.get("/api/books")
    def books():
        return library.books(con)

    @app.get("/api/versions/{title}")
    def versions(title: str):
        return library.versions_of(con, title)

    @app.get("/api/chapters")
    def chapters(version_id: int):
        return library.chapters(con, version_id)

    @app.get("/api/text")
    def text(version_id: int, ref: str):
        return library.chapter(con, version_id, ref)

    @app.get("/api/search")
    def search(q: str):
        if len(q.strip()) < 2:
            raise HTTPException(400, "query too short")
        return library.search(con, q.strip())

    @app.get("/api/commentary")
    def commentary(ref: str):
        rows = con.execute("SELECT * FROM events WHERE kind='commentary' AND (ref=? OR ref LIKE ?) ORDER BY ts",
                           (ref, ref + ":%"))
        return decorate([ledger.row_to_event(r) for r in rows])

    @app.get("/api/thread/{event_id}")
    def thread(event_id: str):
        rows = con.execute("SELECT * FROM events WHERE kind='reply' AND target=? ORDER BY ts", (event_id,))
        return decorate([ledger.row_to_event(r) for r in rows])

    @app.get("/api/feed")
    def feed(limit: int = 50):
        rows = con.execute("SELECT * FROM events WHERE kind IN ('article','commentary') ORDER BY ts DESC LIMIT ?", (limit,))
        return decorate([ledger.row_to_event(r) for r in rows])

    @app.post("/api/events")
    def post(p: PostIn):
        if p.kind in ("grant_role", "revoke_role"):
            raise HTTPException(403, "role changes are made by the authority via the CLI")
        try:
            return node.post(p.user, p.kind, p.body, ref=p.ref, target=p.target)
        except KeyError:
            raise HTTPException(404, "no such local user")
        except (LedgerError, ValueError) as e:
            raise HTTPException(400, str(e))

    @app.get("/api/drafts")
    def drafts():
        return beitdin.list_drafts(con)

    @app.get("/api/drafts/{draft_id}")
    def draft(draft_id: str):
        try:
            return beitdin.draft_status(con, draft_id)
        except KeyError:
            raise HTTPException(404, "no such draft")

    @app.get("/api/users")
    def users():
        R, N = ledger.roles(con), ledger.names(con)
        out = []
        for u in node.local_users():
            pk = node.identity(u).pubkey
            out.append({"user": u, "name": N.get(pk, u), "roles": sorted(R.get(pk, set())), "pubkey": pk})
        return out

    @app.get("/api/legal")
    def legal_report():
        counts = {r["decision"]: r["n"] for r in con.execute("SELECT decision, COUNT(*) n FROM legal_log GROUP BY decision")}
        reasons = [dict(r) for r in con.execute(
            "SELECT CASE WHEN reason LIKE 'מסומן נחלת הכלל אך נראה כיצירה מודרנית%' THEN 'מסומן נחלת הכלל אך נראה כיצירה מודרנית: דורש אימות ידני' ELSE reason END AS reason, COUNT(*) n FROM legal_log WHERE decision='rejected' GROUP BY 1 ORDER BY n DESC")]
        rejected = [dict(r) for r in con.execute(
            "SELECT title, version_title, license, reason FROM legal_log WHERE decision='rejected' ORDER BY id DESC LIMIT 300")]
        return {"counts": counts, "reasons": reasons, "rejected_sample": rejected, "attribution": library.attribution(con),
                "segments": con.execute("SELECT COUNT(*) FROM segments").fetchone()[0],
                "versions": con.execute("SELECT COUNT(*) FROM versions").fetchone()[0]}

    @app.get("/api/meta")
    def meta():
        return {"kinds": ledger.KINDS, "roles": ledger.ROLES, "draft_notice": beitdin.DRAFT_NOTICE}

    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    return app
