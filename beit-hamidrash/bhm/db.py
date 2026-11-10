"""SQLite storage for one node: library texts, the signed event ledger and the legal log."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS versions (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,            -- canonical book title, e.g. Genesis
  he_title TEXT,
  version_title TEXT NOT NULL,
  language TEXT NOT NULL,
  license TEXT NOT NULL,
  tier TEXT NOT NULL,             -- certain / conditional
  obligations TEXT,               -- JSON list
  version_source TEXT,
  categories TEXT,                -- JSON list
  section_names TEXT,             -- JSON list
  origin TEXT NOT NULL,           -- where we fetched it from
  sha256 TEXT NOT NULL,           -- hash of the original file
  imported_at TEXT NOT NULL,
  UNIQUE(title, version_title, language)
);
CREATE TABLE IF NOT EXISTS segments (
  version_id INTEGER NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
  ref TEXT NOT NULL,              -- "Genesis 1:1"
  path TEXT NOT NULL,             -- "1.1" (1-based, dotted)
  seq INTEGER NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY(version_id, path)
);
CREATE INDEX IF NOT EXISTS seg_ref ON segments(ref);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,            -- sha256 of canonical payload
  author TEXT NOT NULL,           -- Ed25519 public key (base64)
  kind TEXT NOT NULL,
  ref TEXT,                       -- text anchor, if any
  target TEXT,                    -- another event id, if any
  body TEXT NOT NULL,             -- JSON
  ts TEXT NOT NULL,
  sig TEXT NOT NULL,
  received_at TEXT NOT NULL,
  origin TEXT NOT NULL            -- local / bundle:<id> / peer:<id>
);
CREATE INDEX IF NOT EXISTS ev_ref ON events(ref);
CREATE INDEX IF NOT EXISTS ev_kind ON events(kind);
CREATE INDEX IF NOT EXISTS ev_target ON events(target);
CREATE TABLE IF NOT EXISTS legal_log (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  origin TEXT NOT NULL,
  title TEXT,
  version_title TEXT,
  language TEXT,
  license TEXT,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trusted_authorities (
  pubkey TEXT PRIMARY KEY,        -- may sign bundles and grant roles
  name TEXT NOT NULL,
  added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS imported_bundles (
  id TEXT PRIMARY KEY,            -- sha256 of the manifest
  authority TEXT NOT NULL,
  created TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  events INTEGER NOT NULL,
  versions INTEGER NOT NULL
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    return con
