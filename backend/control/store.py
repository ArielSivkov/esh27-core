"""
Storage for HITL requests and the global stop switch.

SQLite at CONTROL_DB. On Cloud Run the file lives in one instance only, so run the
service with --max-instances=1 (or swap this module for Firestore) before relying on it.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass, field

URGENCIES = ("info", "normal", "blocking")
OPEN = "open"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hitl_requests (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    question TEXT NOT NULL,
    options TEXT NOT NULL,
    urgency TEXT NOT NULL,
    sensitive INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,          -- open | answered | expired | cancelled
    answer TEXT,
    answered_via TEXT,             -- telegram | phone
    created_at REAL NOT NULL,
    answered_at REAL,
    reminders INTEGER NOT NULL DEFAULT 0,
    calls INTEGER NOT NULL DEFAULT 0,
    last_nudge_at REAL,
    telegram_message_id INTEGER
);
CREATE TABLE IF NOT EXISTS control_flags (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);
"""


@dataclass
class Request:
    id: str
    agent: str
    question: str
    options: list[str]
    urgency: str
    sensitive: bool
    status: str
    created_at: float
    answer: str | None = None
    answered_via: str | None = None
    answered_at: float | None = None
    reminders: int = 0
    calls: int = 0
    last_nudge_at: float | None = None
    telegram_message_id: int | None = None
    extra: dict = field(default_factory=dict)

    def public(self) -> dict:
        return {"id": self.id, "agent": self.agent, "question": self.question, "options": self.options,
                "urgency": self.urgency, "status": self.status, "answer": self.answer,
                "answered_via": self.answered_via, "created_at": self.created_at,
                "answered_at": self.answered_at, "reminders": self.reminders, "calls": self.calls}


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("CONTROL_DB", "/tmp/esh27-control.db")
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA)

    def _row(self, r: sqlite3.Row | None) -> Request | None:
        if r is None:
            return None
        d = dict(r)
        d["options"] = json.loads(d["options"])
        d["sensitive"] = bool(d["sensitive"])
        return Request(**d)

    def create(self, agent: str, question: str, options: list[str] | None = None,
               urgency: str = "normal", sensitive: bool = False, now: float | None = None) -> Request:
        if urgency not in URGENCIES:
            raise ValueError(f"urgency must be one of {URGENCIES}")
        question = question.strip()
        if not question:
            raise ValueError("question is empty")
        opts = [o.strip() for o in (options or ["כן", "לא"]) if o and o.strip()][:4]
        rid = secrets.token_hex(4)
        with self._lock:
            self._db.execute(
                "INSERT INTO hitl_requests (id, agent, question, options, urgency, sensitive, status, created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (rid, agent.strip()[:80] or "agent", question[:1500], json.dumps(opts, ensure_ascii=False),
                 urgency, int(sensitive), OPEN, now or time.time()))
            self._db.commit()
        return self.get(rid)

    def get(self, rid: str) -> Request | None:
        return self._row(self._db.execute("SELECT * FROM hitl_requests WHERE id=?", (rid,)).fetchone())

    def open_requests(self) -> list[Request]:
        rows = self._db.execute("SELECT * FROM hitl_requests WHERE status=? ORDER BY created_at", (OPEN,))
        return [self._row(r) for r in rows.fetchall()]

    def answer(self, rid: str, answer: str, via: str, now: float | None = None) -> bool:
        """Record the first answer only; later clicks on a closed request are ignored."""
        with self._lock:
            cur = self._db.execute(
                "UPDATE hitl_requests SET status='answered', answer=?, answered_via=?, answered_at=?"
                " WHERE id=? AND status=?", (answer[:1500], via, now or time.time(), rid, OPEN))
            self._db.commit()
        return cur.rowcount == 1

    def close(self, rid: str, status: str, now: float | None = None) -> bool:
        with self._lock:
            cur = self._db.execute("UPDATE hitl_requests SET status=?, answered_at=? WHERE id=? AND status=?",
                                   (status, now or time.time(), rid, OPEN))
            self._db.commit()
        return cur.rowcount == 1

    def note_nudge(self, rid: str, kind: str, now: float | None = None) -> None:
        col = {"remind": "reminders", "call": "calls"}[kind]
        with self._lock:
            self._db.execute(f"UPDATE hitl_requests SET {col}={col}+1, last_nudge_at=? WHERE id=?",
                             (now or time.time(), rid))
            self._db.commit()

    def set_message_id(self, rid: str, message_id: int) -> None:
        with self._lock:
            self._db.execute("UPDATE hitl_requests SET telegram_message_id=? WHERE id=?", (message_id, rid))
            self._db.commit()

    def by_message_id(self, message_id: int) -> Request | None:
        return self._row(self._db.execute(
            "SELECT * FROM hitl_requests WHERE telegram_message_id=?", (message_id,)).fetchone())

    def recent(self, limit: int = 10) -> list[Request]:
        rows = self._db.execute("SELECT * FROM hitl_requests ORDER BY created_at DESC LIMIT ?", (limit,))
        return [self._row(r) for r in rows.fetchall()]

    # Stop switch: /stop in Telegram pauses every agent that checks control_status.
    def set_flag(self, name: str, value: str) -> None:
        with self._lock:
            self._db.execute("INSERT INTO control_flags (name, value, updated_at) VALUES (?,?,?)"
                             " ON CONFLICT(name) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                             (name, value, time.time()))
            self._db.commit()

    def flag(self, name: str, default: str = "") -> str:
        r = self._db.execute("SELECT value FROM control_flags WHERE name=?", (name,)).fetchone()
        return r["value"] if r else default

    @property
    def paused(self) -> bool:
        return self.flag("paused") == "1"


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
