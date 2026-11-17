"""Profiles and following: /api/profiles. Read-only views computed from the signed ledger.

Follow state is replayed from follow/unfollow events (latest wins per pair).
Hidden events (ledger.hidden) are excluded everywhere.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from .. import ledger
from ..signing import fingerprint

NAV = {"label": "אנשים", "href": "#/people"}

POST_KINDS = ("commentary", "article", "reply", "sheet", "psak_draft")
FEED_KINDS = ("commentary", "article", "sheet")


def _follow_graph(con, hidden: set[str]) -> dict[tuple[str, str], bool]:
    state: dict[tuple[str, str], bool] = {}
    for r in con.execute("SELECT id, author, kind, body FROM events WHERE kind IN ('follow','unfollow') ORDER BY ts, id"):
        if r["id"] in hidden:
            continue
        try:
            subj = json.loads(r["body"]).get("subject")
        except ValueError:
            continue
        if subj and subj != r["author"]:
            state[(r["author"], subj)] = r["kind"] == "follow"
    return state


def make_router(node) -> APIRouter:
    r = APIRouter()
    # own table (kept for future per-profile settings); created idempotently
    node.con.execute("CREATE TABLE IF NOT EXISTS profiles_meta (k TEXT PRIMARY KEY, v TEXT)")
    node.con.commit()

    def ctx():
        c = node.con
        return c, ledger.hidden(c), ledger.roles(c), ledger.names(c)

    def brief_lists(c, hidden, pk):
        g = _follow_graph(c, hidden)
        followers = sorted(a for (a, s), v in g.items() if v and s == pk)
        following = sorted(s for (a, s), v in g.items() if v and a == pk)
        return followers, following

    @r.get("/api/profiles")
    def list_profiles():
        c, hidden, R, N = ctx()
        people: dict[str, int] = {}
        owner: dict[str, str] = {}
        for row in c.execute("SELECT id, author, kind FROM events"):
            owner[row["id"]] = row["author"]
            if row["id"] in hidden:
                continue
            people.setdefault(row["author"], 0)
            if row["kind"] in POST_KINDS:
                people[row["author"]] += 1
        for pk in N:
            people.setdefault(pk, 0)
        g = _follow_graph(c, hidden)
        ends: dict[str, int] = {}
        for row in c.execute("SELECT id, target FROM events WHERE kind='endorse'"):
            if row["id"] in hidden or row["target"] in hidden:
                continue
            o = owner.get(row["target"])
            if o:
                ends[o] = ends.get(o, 0) + 1
        out = []
        for pk, n in people.items():
            out.append({"pubkey": pk, "name": N.get(pk) or pk[:10], "fingerprint": fingerprint(pk),
                        "roles": sorted(R.get(pk, set())), "posts": n, "endorsements": ends.get(pk, 0),
                        "followers": sum(1 for (a, s), v in g.items() if v and s == pk),
                        "following": sum(1 for (a, s), v in g.items() if v and a == pk)})
        out.sort(key=lambda x: (-x["posts"], x["name"]))
        return out

    @r.get("/api/profiles/{pubkey:path}/feed")
    def feed(pubkey: str, limit: int = 50):
        c, hidden, R, N = ctx()
        limit = max(1, min(limit, 200))
        _, following = brief_lists(c, hidden, pubkey)
        if not following:
            return []
        ends: dict[str, set[str]] = {}
        for row in c.execute("SELECT id, target, author FROM events WHERE kind='endorse'"):
            if row["id"] not in hidden:
                ends.setdefault(row["target"], set()).add(row["author"])
        q = ",".join("?" * len(following))
        k = ",".join("?" * len(FEED_KINDS))
        rows = c.execute(f"SELECT * FROM events WHERE author IN ({q}) AND kind IN ({k}) ORDER BY ts DESC, id",
                         (*following, *FEED_KINDS))
        out = []
        for row in rows:
            if row["id"] in hidden:
                continue
            e = ledger.row_to_event(row)
            en = ends.get(e["id"], set())
            out.append({**e, "author_name": N.get(e["author"], e["author"][:10]),
                        "author_roles": sorted(R.get(e["author"], set())), "endorsements": len(en),
                        "scholar_endorsements": sum(1 for a in en if "talmid_chacham" in R.get(a, set()))})
            if len(out) >= limit:
                break
        return out

    @r.get("/api/profiles/{pubkey:path}")
    def get_profile(pubkey: str):
        c, hidden, R, N = ctx()
        known = c.execute("SELECT 1 FROM events WHERE author=? LIMIT 1", (pubkey,)).fetchone() or pubkey in N
        if not known:
            raise HTTPException(404, "no such profile")
        by_kind: dict[str, int] = {}
        for row in c.execute("SELECT id, kind FROM events WHERE author=?", (pubkey,)):
            if row["id"] not in hidden and row["kind"] in POST_KINDS:
                by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
        endorsers: dict[str, set[str]] = {}
        for row in c.execute("SELECT e.id, e.author, e.target FROM events e JOIN events t ON t.id=e.target "
                             "WHERE e.kind='endorse' AND t.author=?", (pubkey,)):
            if row["id"] in hidden or row["target"] in hidden:
                continue
            endorsers.setdefault(row["target"], set()).add(row["author"])
        followers, following = brief_lists(c, hidden, pubkey)
        bio = ""
        for row in c.execute("SELECT id, body FROM events WHERE kind='profile' AND author=? ORDER BY ts, id", (pubkey,)):
            if row["id"] not in hidden:
                bio = json.loads(row["body"]).get("bio", "") or bio

        def brief(pks):
            return [{"pubkey": p, "name": N.get(p) or p[:10], "fingerprint": fingerprint(p)} for p in pks]
        return {"pubkey": pubkey, "name": N.get(pubkey) or pubkey[:10], "fingerprint": fingerprint(pubkey),
                "roles": sorted(R.get(pubkey, set())), "bio": bio,
                "posts_by_kind": by_kind, "posts": sum(by_kind.values()),
                "endorsements_received": sum(len(v) for v in endorsers.values()),
                "scholar_endorsements_received": sum(1 for v in endorsers.values() for a in v
                                                     if "talmid_chacham" in R.get(a, set())),
                "unique_endorsers": len(set().union(*endorsers.values())) if endorsers else 0,
                "followers": brief(followers), "following": brief(following),
                "followers_count": len(followers), "following_count": len(following)}

    return r
