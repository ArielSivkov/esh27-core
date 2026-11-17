"""Source sheets (דפי מקורות): ordered lists of library refs and free text, published as signed "sheet" events."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import ledger

NAV = {"label": "דפי מקורות", "href": "#/sheets"}
MAX_ITEMS = 200
MAX_RESOLVE = 100  # items resolved per sheet
MAX_SEGS = 120  # segments returned for a single ref item


class PreviewIn(BaseModel):
    items: list[dict]


def _resolve(con, ref: str) -> dict:
    """Resolve a ref (segment 'Genesis 1:1' or chapter 'Genesis 1') from the first version that has it."""
    ref = (ref or "").strip()
    out = {"ref": ref, "ok": False}
    if not ref:
        return out
    row = con.execute(
        """SELECT v.id, v.version_title, v.license, v.tier, v.version_source FROM segments s JOIN versions v ON v.id=s.version_id
           WHERE s.ref=? OR (s.ref >= ? AND s.ref < ?) ORDER BY (v.language='he') DESC, (v.tier='certain') DESC, v.id LIMIT 1""",
        (ref, ref + ":", ref + ";")).fetchone()
    if not row:
        return out
    segs = con.execute("SELECT ref, text FROM segments WHERE version_id=? AND (ref=? OR (ref >= ? AND ref < ?)) ORDER BY seq LIMIT ?",
                       (row["id"], ref, ref + ":", ref + ";", MAX_SEGS)).fetchall()
    return {"ref": ref, "ok": True, "text": "\n".join(s["text"] for s in segs),
            "segments": [{"ref": s["ref"], "text": s["text"]} for s in segs],
            "version": row["version_title"], "license": row["license"], "tier": row["tier"],
            "source": row["version_source"]}


def _resolve_items(con, items: list) -> list[dict]:
    out = []
    for it in items[:MAX_RESOLVE]:
        if not isinstance(it, dict):
            out.append({"type": "text", "text": "", "ok": False})
        elif isinstance(it.get("ref"), str) and it["ref"]:
            out.append({"type": "ref", **_resolve(con, str(it["ref"]))})
        else:
            out.append({"type": "text", "text": str(it.get("text", "")), "ok": True})
    return out


def make_router(node) -> APIRouter:
    r = APIRouter()

    def sheet_events(con):
        H = ledger.hidden(con)
        N = ledger.names(con)
        for row in con.execute("SELECT * FROM events WHERE kind='sheet' ORDER BY ts DESC, id"):
            e = ledger.row_to_event(row)
            if e["id"] in H or not isinstance(e["body"], dict) or not isinstance(e["body"].get("items"), list):
                continue
            e["author_name"] = N.get(e["author"], e["author"][:10])
            yield e

    @r.get("/api/sheets")
    def list_sheets(limit: int = 100):
        out = []
        for e in sheet_events(node.con):
            b = e["body"]
            out.append({"id": e["id"], "title": b.get("title", ""), "author": e["author"], "author_name": e["author_name"],
                        "ts": e["ts"], "items": len(b["items"]),
                        "refs": sum(1 for i in b["items"] if isinstance(i, dict) and i.get("ref"))})
            if len(out) >= max(1, min(limit, 500)):
                break
        return out

    @r.post("/api/sheets/preview")
    def preview(p: PreviewIn):
        if len(p.items) > MAX_ITEMS:
            raise HTTPException(400, f"at most {MAX_ITEMS} items")
        items = _resolve_items(node.con, p.items)
        return {"items": items, "ok": all(i["ok"] for i in items)}

    @r.get("/api/sheets/{sheet_id}")
    def get_sheet(sheet_id: str):
        for e in sheet_events(node.con):
            if e["id"] == sheet_id:
                b = e["body"]
                return {"id": e["id"], "title": b.get("title", ""), "notes": b.get("notes", ""), "author": e["author"],
                        "author_name": e["author_name"], "ts": e["ts"], "items": _resolve_items(node.con, b["items"])}
        raise HTTPException(404, "sheet not found")

    return r
