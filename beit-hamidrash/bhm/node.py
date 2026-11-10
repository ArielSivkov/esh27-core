"""A node = one computer in a beit midrash: its database, its local identities, its authority key."""
from __future__ import annotations

import os
import re
import threading
from pathlib import Path

from . import db, ledger
from .signing import Identity

HOME = Path(os.environ.get("BHM_HOME", Path(__file__).resolve().parent.parent / "var"))
NAME_OK = re.compile(r"^[\w\-א-ת]{2,40}$")


class Node:
    def __init__(self, home: Path = HOME):
        self.home = Path(home)
        self.keys = self.home / "keys"
        self._local = threading.local()
        db.connect(self.home / "library.db")   # create schema once

    @property
    def con(self):
        """One SQLite connection per thread: the web server handles requests in a thread pool."""
        c = getattr(self._local, "con", None)
        if c is None:
            c = self._local.con = db.connect(self.home / "library.db")
        return c

    # identities ------------------------------------------------------------
    def identity(self, name: str) -> Identity:
        if not NAME_OK.match(name):
            raise ValueError("invalid name")
        p = self.keys / f"{name}.pem"
        if not p.exists():
            raise KeyError(name)
        return Identity.load(p)

    def local_users(self) -> list[str]:
        return sorted(p.stem for p in self.keys.glob("*.pem")) if self.keys.exists() else []

    def create_user(self, name: str, display: str | None = None) -> Identity:
        if not NAME_OK.match(name):
            raise ValueError("invalid name")
        p = self.keys / f"{name}.pem"
        if p.exists():
            raise FileExistsError(name)
        ident = Identity.generate()
        ident.save(p)
        ledger.insert(self.con, ledger.make_event(ident, "profile", {"name": display or name}))
        return ident

    def init_authority(self, name: str = "authority", display: str = "רשות העדכונים") -> Identity:
        p = self.keys / f"{name}.pem"
        ident = Identity.load(p) if p.exists() else self.create_user(name, display)
        self.trust(ident.pubkey, display)
        return ident

    def trust(self, pubkey: str, name: str) -> None:
        self.con.execute("INSERT OR REPLACE INTO trusted_authorities(pubkey,name,added_at) VALUES (?,?,?)",
                         (pubkey, name, ledger.now()))
        self.con.commit()

    def post(self, user: str, kind: str, body: dict, ref: str | None = None, target: str | None = None) -> dict:
        ev = ledger.make_event(self.identity(user), kind, body, ref=ref, target=target)
        ledger.insert(self.con, ev)
        return ev
