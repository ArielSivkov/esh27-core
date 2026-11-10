"""CLI: python -m bhm <command>

  init                         create the node's authority key and trust it
  user add NAME [DISPLAY]      create a local identity
  grant NAME ROLE              authority grants talmid_chacham / moderator / dayan
  revoke NAME ROLE
  trust PUBKEY NAME            trust another authority (for bundles from elsewhere)
  harvest [PREFIX] [--no-b]    import the Sefaria export through the legal gate
  legal                        legal department report
  bundle export DIR [--since TS] [--no-library] [--title T ...]
  bundle verify DIR
  bundle import DIR
  serve [--port 8000]
"""
from __future__ import annotations

import argparse
import json
import sys

from . import bundle, ledger, sefaria
from .node import Node


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bhm")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    u = sub.add_parser("user"); u.add_argument("action", choices=["add"]); u.add_argument("name"); u.add_argument("display", nargs="?")
    for c in ("grant", "revoke"):
        g = sub.add_parser(c); g.add_argument("name"); g.add_argument("role", choices=list(ledger.ROLES))
    t = sub.add_parser("trust"); t.add_argument("pubkey"); t.add_argument("name")
    h = sub.add_parser("harvest"); h.add_argument("prefix", nargs="?", default="json/"); h.add_argument("--no-b", action="store_true")
    sub.add_parser("legal")
    b = sub.add_parser("bundle"); b.add_argument("action", choices=["export", "verify", "import"]); b.add_argument("dir")
    b.add_argument("--since"); b.add_argument("--no-library", action="store_true"); b.add_argument("--title", action="append")
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8000); s.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args(argv)
    node = Node()

    if a.cmd == "init":
        ident = node.init_authority()
        print("authority:", ident.pubkey)
    elif a.cmd == "user":
        print(node.create_user(a.name, a.display).pubkey)
    elif a.cmd in ("grant", "revoke"):
        subject = node.identity(a.name).pubkey
        ev = node.post("authority", f"{a.cmd}_role", {"subject": subject, "role": a.role})
        print(ev["id"])
    elif a.cmd == "trust":
        node.trust(a.pubkey, a.name)
    elif a.cmd == "harvest":
        print(sefaria.harvest(node.con, a.prefix, allow_tier_b=not a.no_b))
    elif a.cmd == "legal":
        for r in node.con.execute("SELECT decision, COUNT(*) n FROM legal_log GROUP BY decision"):
            print(r["decision"], r["n"])
        for r in node.con.execute("SELECT CASE WHEN reason LIKE 'מסומן נחלת הכלל אך נראה כיצירה מודרנית%' THEN 'מסומן נחלת הכלל אך נראה כיצירה מודרנית: דורש אימות ידני' ELSE reason END AS reason, COUNT(*) n FROM legal_log WHERE decision='rejected' GROUP BY 1 ORDER BY n DESC"):
            print(f"  {r['n']:6d}  {r['reason']}")
    elif a.cmd == "bundle":
        if a.action == "export":
            m = bundle.export_bundle(node.con, node.identity("authority"), a.dir, since=a.since,
                                     include_library=not a.no_library, titles=a.title)
            print(json.dumps(m["counts"]))
        elif a.action == "verify":
            m = bundle.verify_bundle(node.con, a.dir)
            print("OK", json.dumps(m["counts"]))
        else:
            print(json.dumps(bundle.import_bundle(node.con, a.dir), ensure_ascii=False))
    elif a.cmd == "serve":
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(node), host=a.host, port=a.port)


if __name__ == "__main__":
    sys.exit(main())
