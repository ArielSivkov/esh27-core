"""Moderation queue: reports (kind "report") on events, and the list of hidden events.

Hiding never deletes anything: the signed history stays in the ledger and is
verifiable. Only `hide`/`unhide` events by a moderator or trusted authority count
(see ledger.hidden); the same replay rules are used here.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request

from .. import ledger

NAV = {"label": "פיקוח תוכן", "href": "#/moderation"}


def make_router(node) -> APIRouter:
    r = APIRouter(prefix="/api/moderation")

    class _Con:  # resolves to the calling thread's connection
        def __getattr__(self, k):
            return getattr(node.con, k)
    con = _Con()

    def viewer(as_user):
        if not as_user:
            return {"as": None, "is_moderator": False}
        try:
            pk = node.identity(as_user).pubkey
        except Exception:
            raise HTTPException(404, "no such local user")
        is_mod = "moderator" in ledger.roles(con).get(pk, set()) or pk in ledger.trusted(con)
        return {"as": as_user, "is_moderator": is_mod}

    def privileged(request, v):
        local = request.client is not None and request.client.host in ("127.0.0.1", "::1", "testclient")
        return bool(local and v["as"] and v["is_moderator"])

    def summary(ev_id, N):
        row = con.execute("SELECT * FROM events WHERE id=?", (ev_id,)).fetchone()
        if not row:
            return {"id": ev_id, "missing": True, "kind": "", "text": "", "title": "", "author_name": "", "ts": ""}
        e = ledger.row_to_event(row)
        b = e["body"]
        return {"id": e["id"], "kind": e["kind"], "ref": e["ref"], "ts": e["ts"],
                "author": e["author"], "author_name": N.get(e["author"], e["author"][:10]),
                "title": str(b.get("title", "")), "text": str(b.get("text", ""))[:600]}

    @r.get("/queue")
    def queue(request: Request, as_user: str | None = Query(None, alias="as")):
        v = viewer(as_user)
        priv = privileged(request, v)
        H, N = ledger.hidden(con), ledger.names(con)
        reports: dict[str, list] = {}
        for x in con.execute("SELECT * FROM events WHERE kind='report' ORDER BY ts, id"):
            b = json.loads(x["body"])
            reports.setdefault(x["target"], []).append(
                {"by": x["author"], "by_name": N.get(x["author"], x["author"][:10]),
                 "reason": str(b.get("reason", "")), "ts": x["ts"]})
        items = []
        for tid, rs in reports.items():
            if tid in H:
                continue
            cnt = len({q["by"] for q in rs})
            items.append({**summary(tid, N), "report_count": cnt, "reports": rs} if priv
                         else {"id": tid, "report_count": cnt})
        items.sort(key=lambda i: (-i["report_count"], i["id"]))
        return {**v, "items": items, "count": len(items),
                "note": "הסתרה אינה מוחקת: ההיסטוריה החתומה נשמרת, והאירוע חוזר להופיע בביטול ההסתרה."}

    @r.get("/hidden")
    def hidden(request: Request, as_user: str | None = Query(None, alias="as")):
        v = viewer(as_user)
        priv = privileged(request, v)
        H, N = ledger.hidden(con), ledger.names(con)
        R, auth = ledger.roles(con), ledger.trusted(con)
        last: dict[str, dict] = {}
        for x in con.execute("SELECT * FROM events WHERE kind IN ('hide','unhide') ORDER BY ts, id"):
            if x["author"] in auth or "moderator" in R.get(x["author"], set()):
                last[x["target"]] = {"by": x["author"], "by_name": N.get(x["author"], x["author"][:10]),
                                     "reason": str(json.loads(x["body"]).get("reason", "")), "ts": x["ts"]}
        items = [{**summary(t, N), "hidden_by": last[t]} if priv else {"id": t}
                 for t in sorted(H) if t in last]
        return {**v, "items": items, "count": len(items)}

    return r
