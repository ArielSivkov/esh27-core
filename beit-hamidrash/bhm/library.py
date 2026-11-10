"""הספרייה הגדולה: storage and lookup of text versions, segment by segment."""
from __future__ import annotations

import json
import re

from . import legal
from .ledger import now


def _flatten(node, prefix: list[int]):
    """Yield (path, text) for nested lists of strings. Paths are 1-based."""
    if isinstance(node, str):
        if node.strip():
            yield prefix, node
        return
    if isinstance(node, list):
        for i, child in enumerate(node, 1):
            yield from _flatten(child, prefix + [i])


def iter_segments(title: str, text):
    """Handles simple texts (nested lists) and complex texts (dict of named nodes)."""
    if isinstance(text, dict):
        for name, sub in text.items():
            label = title if name in ("", "default") else f"{title}, {name}"
            yield from iter_segments(label, sub)
        return
    for path, t in _flatten(text, []):
        if not path:
            yield f"{title}", "0", t
        else:
            yield f"{title} {':'.join(map(str, path))}", ".".join(map(str, path)) + "@" + title, t


TAG = re.compile(r"<[^>]+>")


def clean(t: str) -> str:
    return TAG.sub("", t).replace("&nbsp;", " ").strip()


def import_version(con, meta: dict, origin: str, sha: str, allow_tier_b: bool = False) -> tuple[bool, legal.Decision, int]:
    """Run the legal gate, then store. Returns (imported, decision, segment_count)."""
    dec = legal.review(meta, allow_tier_b=allow_tier_b)
    con.execute("INSERT INTO legal_log(at,origin,title,version_title,language,license,decision,reason) VALUES (?,?,?,?,?,?,?,?)",
                (now(), origin, meta.get("title"), meta.get("versionTitle"), meta.get("language"),
                 meta.get("license"), dec.tier, dec.reason))
    if not dec.allowed:
        con.commit()
        return False, dec, 0
    con.execute("DELETE FROM versions WHERE title=? AND version_title=? AND language=?",
                (meta["title"], meta["versionTitle"], meta.get("language", "he")))
    cur = con.execute(
        "INSERT INTO versions(title,he_title,version_title,language,license,tier,obligations,version_source,categories,section_names,origin,sha256,imported_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (meta["title"], meta.get("heTitle"), meta["versionTitle"], meta.get("language", "he"), meta.get("license", ""),
         dec.tier, json.dumps(dec.obligations, ensure_ascii=False), meta.get("versionSource"),
         json.dumps(meta.get("categories") or [], ensure_ascii=False),
         json.dumps(meta.get("sectionNames") or [], ensure_ascii=False), origin, sha, now()))
    vid = cur.lastrowid
    rows = [(vid, ref, path, i, clean(t)) for i, (ref, path, t) in enumerate(iter_segments(meta["title"], meta["text"]))]
    con.executemany("INSERT OR REPLACE INTO segments(version_id,ref,path,seq,text) VALUES (?,?,?,?,?)", rows)
    con.commit()
    return True, dec, len(rows)


def books(con) -> list[dict]:
    q = """SELECT v.title, v.he_title, v.categories, COUNT(*) AS versions, GROUP_CONCAT(v.version_title, ' | ') AS vts
           FROM versions v GROUP BY v.title ORDER BY v.categories, v.title"""
    return [{"title": r["title"], "he_title": r["he_title"], "categories": json.loads(r["categories"]),
             "versions": r["versions"], "version_titles": r["vts"]} for r in con.execute(q)]


def versions_of(con, title: str) -> list[dict]:
    return [dict(r) | {"obligations": json.loads(r["obligations"] or "[]")}
            for r in con.execute("SELECT id,title,he_title,version_title,language,license,tier,obligations,version_source FROM versions WHERE title=? ORDER BY tier, version_title", (title,))]


def chapters(con, version_id: int) -> list[str]:
    """Distinct chapter-level refs of a version, in order ("Genesis 1", "Genesis 2", ...)."""
    out, seen = [], set()
    for r in con.execute("SELECT ref FROM segments WHERE version_id=? ORDER BY seq", (version_id,)):
        ref = r["ref"]
        c = ref.rsplit(":", 1)[0] if ":" in ref else ref
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def chapter(con, version_id: int, ref_prefix: str) -> list[dict]:
    """All segments whose ref starts with `ref_prefix:` (e.g. 'Genesis 1' -> 'Genesis 1:1'...)."""
    rows = con.execute("SELECT ref, text, seq FROM segments WHERE version_id=? AND (ref=? OR ref LIKE ?) ORDER BY seq",
                       (version_id, ref_prefix, ref_prefix + ":%"))
    return [{"ref": r["ref"], "text": r["text"]} for r in rows]


def search(con, q: str, limit: int = 50) -> list[dict]:
    rows = con.execute("""SELECT s.ref, s.text, v.version_title, v.title FROM segments s JOIN versions v ON v.id=s.version_id
                          WHERE s.text LIKE ? LIMIT ?""", (f"%{q}%", limit))
    return [dict(r) for r in rows]


def attribution(con) -> list[dict]:
    """Attribution notices required by tier-B licenses (shown on the site's sources page)."""
    return [dict(r) for r in con.execute(
        "SELECT title, version_title, license, version_source FROM versions WHERE tier='conditional' ORDER BY title")]
