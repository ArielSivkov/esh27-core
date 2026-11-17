"""Protocol v2 "content envelope" (library module; NOT wired into the core).

A v1 event signs its whole body, so the body can never be erased without
breaking the signature. A v2 event signs `body_hash` = sha256(canonical(body))
instead. The body lives in a separate blob store (`envelope_blobs`) and can be
purged (illegal / harmful content) while the signed event, and its place in
the ledger, stay verifiable. See docs/envelope.md.

Public API: make_event_v2, check_event_v2, verify_v2, body_hash, BlobStore
(put/get/purge/has/is_purged), strip_body, convert_v1_to_v2, make_router.
"""
from __future__ import annotations

import json
import re
import sqlite3

from fastapi import APIRouter

from ..ledger import KINDS, MAX_BODY_BYTES, ROLES, LedgerError, now
from ..signing import Identity, canonical, sha256_hex, verify

PROTOCOL_VERSION = 2
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
SIGNED_FIELDS = ("v", "author", "kind", "ref", "target", "body_hash", "ts")

CONVERT_NOTE = (
    "v1 -> v2 conversion cannot re-sign: a v1 event is signed by its author over the full body, "
    "and only the author's key can produce a v2 signature. convert_v1_to_v2 therefore returns the "
    "blob (body) plus a 'legacy' wrapper that keeps the original v1 event intact; a v2 event for the "
    "same content can only be issued by the author (re-publish) or by a node-key attestation.")

SCHEMA = """CREATE TABLE IF NOT EXISTS envelope_blobs(
  hash TEXT PRIMARY KEY, body TEXT, purged INTEGER NOT NULL DEFAULT 0,
  purged_at TEXT, reason TEXT)"""


def body_hash(body: dict) -> str:
    """sha256 over the canonical JSON of the body."""
    return sha256_hex(canonical(body))


def make_event_v2(identity: Identity, kind: str, body: dict, ref: str | None = None,
                  target: str | None = None, ts: str | None = None) -> dict:
    """Return a v2 event. The signed payload holds `body_hash`, not `body`.

    The returned dict also carries the body under the transient key "body"
    (not signed); use strip_body() before sending it where blobs may not go.
    """
    if not isinstance(body, dict):
        raise LedgerError("body must be an object")
    if len(canonical(body)) > MAX_BODY_BYTES:
        raise LedgerError("event too large")
    payload = {"v": PROTOCOL_VERSION, "author": identity.pubkey, "kind": kind, "ref": ref,
               "target": target, "body_hash": body_hash(body), "ts": ts or now()}
    data = canonical(payload)
    return {**payload, "id": sha256_hex(data), "sig": identity.sign(data), "body": body}


def strip_body(ev: dict) -> dict:
    return {k: v for k, v in ev.items() if k != "body"}


_NEED_TARGET = {"reply", "endorse", "hide", "unhide", "psak_review", "psak_sign", "report", "edit"}


def _check_kind_rules(ev: dict, b: dict | None) -> None:
    """Same per-kind rules as ledger.check_event; body rules only when body `b` is given."""
    kind = ev["kind"]
    if kind in _NEED_TARGET and not ev.get("target"):
        raise LedgerError(f"{kind} requires target")
    if kind == "commentary" and not ev.get("ref"):
        raise LedgerError("commentary requires a text ref")
    if b is None:
        return
    if not isinstance(b, dict):
        raise LedgerError("body must be an object")
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
    if kind in ("follow", "unfollow") and not b.get("subject"):
        raise LedgerError(f"{kind} requires subject (author public key)")
    if kind == "sheet" and (not str(b.get("title", "")).strip() or not isinstance(b.get("items"), list) or not b["items"]):
        raise LedgerError("sheet requires title and a non-empty items list")
    if kind == "edit" and not str(b.get("text", "")).strip():
        raise LedgerError("edit requires the new text")
    if kind == "psak_sign" and b.get("decision") not in ("approved", "rejected"):
        raise LedgerError("psak_sign decision must be approved/rejected")


def check_event_v2(ev: dict, blob: dict | None = None) -> None:
    """Structure + signature + per-kind rules (same as ledger.check_event).

    Target/ref rules always apply; body rules apply when `blob` is given.
    Raises LedgerError.
    """
    for k in ("id", "author", "kind", "body_hash", "ts", "sig"):
        if not ev.get(k):
            raise LedgerError(f"missing field {k}")
    if ev.get("v") != PROTOCOL_VERSION:
        raise LedgerError("not a v2 event")
    if ev["kind"] not in KINDS:
        raise LedgerError(f"unknown kind {ev['kind']}")
    if not isinstance(ev["body_hash"], str) or not _HEX64.match(ev["body_hash"]):
        raise LedgerError("body_hash must be 64 hex chars")
    data = canonical({k: ev.get(k) for k in SIGNED_FIELDS})
    if sha256_hex(data) != ev["id"]:
        raise LedgerError("id does not match content")
    if not verify(ev["author"], data, ev["sig"]):
        raise LedgerError("bad signature")
    if blob is not None:
        if not isinstance(blob, dict):
            raise LedgerError("body must be an object")
        if body_hash(blob) != ev["body_hash"]:
            raise LedgerError("blob does not match body_hash")
    _check_kind_rules(ev, blob)


def verify_v2(ev: dict, blob: dict | None = None) -> bool:
    """True if the event is validly signed and, when a blob is given, matches body_hash.

    With blob=None (purged / not yet fetched) the event is valid on the
    envelope alone: erasing a body never invalidates the signature.
    Returns False (never raises) on any failure.
    """
    try:
        check_event_v2(ev, blob)
    except (LedgerError, TypeError, AttributeError, ValueError):
        return False
    return True


class BlobStore:
    """Blob table `envelope_blobs(hash, body, purged)` on a SQLite connection."""

    def __init__(self, con: sqlite3.Connection):
        self.con = con
        con.execute(SCHEMA)
        con.commit()

    def put(self, body: dict) -> str:
        """Store a body; returns its hash. A purged hash is NOT resurrected (stays tombstoned)."""
        if not isinstance(body, dict):
            raise LedgerError("body must be an object")
        if len(canonical(body)) > MAX_BODY_BYTES:
            raise LedgerError("event too large")
        h = body_hash(body)
        row = self.con.execute("SELECT purged FROM envelope_blobs WHERE hash=?", (h,)).fetchone()
        if row is None:
            self.con.execute("INSERT INTO envelope_blobs(hash,body,purged) VALUES (?,?,0)",
                             (h, canonical(body).decode("utf-8")))
            self.con.commit()
        return h

    def get(self, h: str) -> dict | None:
        """The body, or None if unknown, purged or corrupted (hash re-verified)."""
        row = self.con.execute("SELECT body,purged FROM envelope_blobs WHERE hash=?", (h,)).fetchone()
        if row is None or row[1] or row[0] is None:
            return None
        body = json.loads(row[0])
        return body if body_hash(body) == h else None

    def has(self, h: str) -> bool:
        return self.get(h) is not None

    def is_purged(self, h: str) -> bool:
        row = self.con.execute("SELECT purged FROM envelope_blobs WHERE hash=?", (h,)).fetchone()
        return bool(row and row[0])

    def purge(self, h: str, reason: str | None = None) -> bool:
        """Erase the body, keep the hash row as a tombstone (so re-import is refused).

        Works even if the blob was never stored locally. Returns True if state changed.
        """
        if not _HEX64.match(h or ""):
            raise LedgerError("bad hash")
        row = self.con.execute("SELECT purged FROM envelope_blobs WHERE hash=?", (h,)).fetchone()
        if row and row[0]:
            return False
        if row:
            self.con.execute("UPDATE envelope_blobs SET body=NULL,purged=1,purged_at=?,reason=? WHERE hash=?",
                             (now(), reason, h))
        else:
            self.con.execute("INSERT INTO envelope_blobs(hash,body,purged,purged_at,reason) VALUES (?,NULL,1,?,?)",
                             (h, now(), reason))
        self.con.commit()
        return True

    def stats(self) -> dict:
        r = self.con.execute("SELECT COUNT(*), COALESCE(SUM(purged),0) FROM envelope_blobs").fetchone()
        return {"blobs": r[0], "purged": r[1]}


def convert_v1_to_v2(ev_v1: dict) -> dict:
    """Split a v1 event into pieces a v2 migration can use. Does NOT re-sign.

    Returns {"legacy": <untouched v1 event>, "body_hash", "blob", "note"}.
    The v1 event stays verifiable with ledger.check_event; the blob can be put
    in a BlobStore so that content may later be purged by hash (the v1 event
    itself still embeds the body, so full erasure needs the author to re-issue
    it as v2 -- see docs/envelope.md).
    """
    body = ev_v1.get("body")
    if not isinstance(body, dict):
        raise LedgerError("v1 event has no body")
    return {"legacy": dict(ev_v1), "body_hash": body_hash(body), "blob": body, "note": CONVERT_NOTE}


def make_router(node=None) -> APIRouter:
    r = APIRouter()

    @r.get("/api/envelope/info")
    def info():
        return {
            "name": "envelope", "protocol": PROTOCOL_VERSION, "wired_into_core": False,
            "signed_fields": list(SIGNED_FIELDS),
            "summary": "אירוע v2 חותם על גיבוב התוכן (body_hash) ולא על התוכן עצמו; "
                       "ניתן למחוק תוכן בלתי חוקי בלי לשבור את החתימה או את שרשרת האירועים.",
            "doc": "docs/envelope.md", "note": CONVERT_NOTE,
        }

    return r
