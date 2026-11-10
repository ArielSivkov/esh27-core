"""The signed ledger: every action in the beit midrash is an append-only signed event.

Design rules
------------
* An event is `{author, kind, ref, target, body, ts}`. Its id is the SHA-256 of
  that payload's canonical JSON, and `sig` is the author's Ed25519 signature
  over the same bytes. Events are never edited or deleted.
* Any validly signed event is stored. *Authorization* (who is a dayan, who may
  hide content) is computed when reading, by replaying role grants made by
  trusted authorities. This lets nodes that meet only by USB merge their
  ledgers in any order and still reach the same state.
* Moderation never deletes: a `hide` event by a moderator removes the target
  from display, and the history stays verifiable.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .signing import Identity, canonical, sha256_hex, verify

MAX_BODY_BYTES = 64 * 1024

ROLES = {"talmid_chacham": "תלמיד חכם מאומת", "moderator": "מפקח תוכן", "dayan": "דיין"}

KINDS = {
    "profile": "פרופיל",
    "commentary": "פירוש",
    "article": "מאמר",
    "reply": "תגובה",
    "endorse": "הסכמה",
    "grant_role": "מינוי",
    "revoke_role": "ביטול מינוי",
    "hide": "הסתרה",
    "unhide": "ביטול הסתרה",
    "psak_draft": "טיוטת פסק",
    "psak_review": "הערת עיון לטיוטה",
    "psak_sign": "חתימת דיין",
}


class LedgerError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_event(identity: Identity, kind: str, body: dict, ref: str | None = None,
               target: str | None = None, ts: str | None = None) -> dict:
    payload = {"author": identity.pubkey, "kind": kind, "ref": ref, "target": target,
               "body": body, "ts": ts or now()}
    data = canonical(payload)
    return {**payload, "id": sha256_hex(data), "sig": identity.sign(data)}


def check_event(ev: dict) -> None:
    """Validate structure and signature. Raises LedgerError."""
    for k in ("id", "author", "kind", "body", "ts", "sig"):
        if k not in ev:
            raise LedgerError(f"missing field {k}")
    if ev["kind"] not in KINDS:
        raise LedgerError(f"unknown kind {ev['kind']}")
    if not isinstance(ev["body"], dict):
        raise LedgerError("body must be an object")
    payload = {k: ev.get(k) for k in ("author", "kind", "ref", "target", "body", "ts")}
    data = canonical(payload)
    if len(data) > MAX_BODY_BYTES:
        raise LedgerError("event too large")
    if sha256_hex(data) != ev["id"]:
        raise LedgerError("id does not match content")
    if not verify(ev["author"], data, ev["sig"]):
        raise LedgerError("bad signature")
    b, kind = ev["body"], ev["kind"]
    need_target = {"reply", "endorse", "hide", "unhide", "psak_review", "psak_sign"}
    if kind in need_target and not ev.get("target"):
        raise LedgerError(f"{kind} requires target")
    if kind in ("commentary",) and not ev.get("ref"):
        raise LedgerError("commentary requires a text ref")
    if kind in ("commentary", "reply", "article") and not str(b.get("text", "")).strip():
        raise LedgerError("text is empty")
    if kind == "article" and not str(b.get("title", "")).strip():
        raise LedgerError("article requires title")
    if kind in ("grant_role", "revoke_role") and (b.get("role") not in ROLES or not b.get("subject")):
        raise LedgerError("grant/revoke requires subject and a known role")
    if kind == "psak_draft":
        if not str(b.get("question", "")).strip() or not str(b.get("answer", "")).strip():
            raise LedgerError("draft requires question and answer")
        if not b.get("sources"):
            raise LedgerError("draft requires at least one source")
    if kind == "psak_sign" and b.get("decision") not in ("approved", "rejected"):
        raise LedgerError("psak_sign decision must be approved/rejected")


def insert(con, ev: dict, origin: str = "local") -> bool:
    """Validate and store. Returns False if the event already existed."""
    check_event(ev)
    cur = con.execute(
        "INSERT OR IGNORE INTO events(id,author,kind,ref,target,body,ts,sig,received_at,origin) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (ev["id"], ev["author"], ev["kind"], ev.get("ref"), ev.get("target"),
         json.dumps(ev["body"], ensure_ascii=False), ev["ts"], ev["sig"], now(), origin))
    con.commit()
    return cur.rowcount == 1


def row_to_event(r) -> dict:
    return {"id": r["id"], "author": r["author"], "kind": r["kind"], "ref": r["ref"], "target": r["target"],
            "body": json.loads(r["body"]), "ts": r["ts"], "sig": r["sig"]}


def all_events(con, since: str | None = None):
    q = "SELECT * FROM events" + (" WHERE received_at > ?" if since else "") + " ORDER BY ts, id"
    return [row_to_event(r) for r in con.execute(q, (since,) if since else ())]


# ---------------------------------------------------------------- state replay
def trusted(con) -> set[str]:
    return {r["pubkey"] for r in con.execute("SELECT pubkey FROM trusted_authorities")}


def roles(con) -> dict[str, set[str]]:
    """Replay grant/revoke events signed by trusted authorities, in time order."""
    auth = trusted(con)
    out: dict[str, set[str]] = {}
    for r in con.execute("SELECT * FROM events WHERE kind IN ('grant_role','revoke_role') ORDER BY ts, id"):
        if r["author"] not in auth:
            continue
        b = json.loads(r["body"])
        s = out.setdefault(b["subject"], set())
        (s.add if r["kind"] == "grant_role" else s.discard)(b["role"])
    for a in auth:
        out.setdefault(a, set()).update({"moderator"})
    return out


def hidden(con) -> set[str]:
    """Events currently hidden by a moderator or authority (latest action wins)."""
    R = roles(con)
    auth = trusted(con)
    state: dict[str, bool] = {}
    for r in con.execute("SELECT * FROM events WHERE kind IN ('hide','unhide') ORDER BY ts, id"):
        if r["author"] in auth or "moderator" in R.get(r["author"], set()):
            state[r["target"]] = r["kind"] == "hide"
    return {k for k, v in state.items() if v}


def names(con) -> dict[str, str]:
    out = {}
    for r in con.execute("SELECT author, body FROM events WHERE kind='profile' ORDER BY ts, id"):
        out[r["author"]] = json.loads(r["body"]).get("name", "")
    for r in con.execute("SELECT pubkey, name FROM trusted_authorities"):
        out.setdefault(r["pubkey"], r["name"])
    return out
