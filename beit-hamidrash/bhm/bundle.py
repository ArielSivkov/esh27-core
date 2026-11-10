"""יחידת חיתום נתונים וסייבר: חבילות עדכון לדיסק און קי.

A bundle is a plain directory (no archive, so no zip-slip) containing:

  manifest.json      list of every file with its SHA-256 and size
  manifest.sig       Ed25519 signature of the manifest by a trusted authority
  events.jsonl       signed ledger events
  library/*.jsonl.gz text versions (metadata + segments)

Import is all-or-nothing and refuses the whole bundle if:
  * the signer is not in this node's trusted_authorities
  * the signature or any file hash does not match
  * there is any file not listed in the manifest, a path that escapes the
    bundle, a symlink, or an extension outside the data-only allowlist
  * a file exceeds the size limit
Library versions are re-checked by the *receiving* node's legal gate, and
every event's own signature is verified before it is stored. Nothing in a
bundle is ever executed.
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

from . import library, ledger
from .signing import Identity, canonical, sha256_hex, verify

FORMAT = "bhm-bundle/1"
ALLOWED_EXT = (".jsonl", ".jsonl.gz")
SAFE_PATH = re.compile(r"^[a-z0-9_\-]+(/[a-z0-9_\-]+)*\.(jsonl|jsonl\.gz)$")
MAX_FILE = 512 * 1024 * 1024


class BundleError(ValueError):
    pass


def _write(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"sha256": sha256_hex(data), "size": len(data)}


def export_bundle(con, authority: Identity, out: Path, since: str | None = None,
                  include_library: bool = True, titles: list[str] | None = None) -> dict:
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise BundleError(f"{out} is not empty")
    files = []
    evs = ledger.all_events(con, since)
    data = "\n".join(json.dumps(e, ensure_ascii=False) for e in evs).encode()
    files.append({"path": "events.jsonl", **_write(out / "events.jsonl", data)})
    nver = 0
    if include_library:
        q = "SELECT * FROM versions" + (f" WHERE title IN ({','.join('?' * len(titles))})" if titles else "") + " ORDER BY id"
        for v in con.execute(q, titles or ()):
            segs = [[s["ref"], s["path"], s["seq"], s["text"]] for s in
                    con.execute("SELECT ref,path,seq,text FROM segments WHERE version_id=? ORDER BY seq", (v["id"],))]
            meta = {k: v[k] for k in ("title", "he_title", "version_title", "language", "license", "version_source", "sha256")}
            meta["categories"] = json.loads(v["categories"])
            meta["section_names"] = json.loads(v["section_names"])
            line = json.dumps({"meta": meta, "segments": segs}, ensure_ascii=False).encode()
            rel = f"library/v{v['id']:06d}.jsonl.gz"
            files.append({"path": rel, **_write(out / rel, gzip.compress(line, mtime=0))})
            nver += 1
    manifest = {"format": FORMAT, "created": ledger.now(), "authority": authority.pubkey, "since": since,
                "counts": {"events": len(evs), "versions": nver}, "files": files}
    (out / "manifest.json").write_bytes(json.dumps(manifest, ensure_ascii=False, indent=1).encode())
    (out / "manifest.sig").write_text(authority.sign(canonical(manifest)))
    return manifest


def verify_bundle(con, path: Path) -> dict:
    """Full verification without importing anything. Returns the manifest."""
    path = Path(path)
    try:
        manifest = json.loads((path / "manifest.json").read_bytes())
        sig = (path / "manifest.sig").read_text().strip()
    except (OSError, ValueError) as e:
        raise BundleError(f"cannot read manifest: {e}")
    if manifest.get("format") != FORMAT:
        raise BundleError("unknown bundle format")
    trusted = ledger.trusted(con)
    if manifest.get("authority") not in trusted:
        raise BundleError("bundle is signed by an authority this node does not trust")
    if not verify(manifest["authority"], canonical(manifest), sig):
        raise BundleError("manifest signature is invalid")
    listed = {f["path"]: f for f in manifest["files"]}
    root = path.resolve()
    for p in path.rglob("*"):
        rel = p.relative_to(path).as_posix()
        if p.is_symlink():
            raise BundleError(f"symlink not allowed: {rel}")
        if p.is_dir() or rel in ("manifest.json", "manifest.sig"):
            continue
        if rel not in listed:
            raise BundleError(f"file not in manifest: {rel}")
    for rel, f in listed.items():
        if not SAFE_PATH.match(rel) or not rel.endswith(ALLOWED_EXT):
            raise BundleError(f"forbidden path or type: {rel}")
        fp = (path / rel).resolve()
        if root not in fp.parents:
            raise BundleError(f"path escapes bundle: {rel}")
        if not fp.is_file():
            raise BundleError(f"missing file: {rel}")
        if fp.stat().st_size > MAX_FILE or fp.stat().st_size != f["size"]:
            raise BundleError(f"size mismatch or too large: {rel}")
        if sha256_hex(fp.read_bytes()) != f["sha256"]:
            raise BundleError(f"hash mismatch: {rel}")
    return manifest


def import_bundle(con, path: Path, allow_tier_b: bool = True) -> dict:
    path = Path(path)
    manifest = verify_bundle(con, path)
    bid = sha256_hex(canonical(manifest))
    if con.execute("SELECT 1 FROM imported_bundles WHERE id=?", (bid,)).fetchone():
        return {"bundle": bid, "status": "already imported"}
    # parse and validate everything before writing anything
    events = []
    for line in (path / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            ev = json.loads(line)
            ledger.check_event(ev)
            events.append(ev)
    stats = {"events_new": 0, "events_known": 0, "versions_imported": 0, "versions_rejected": 0}
    for f in manifest["files"]:
        if not f["path"].startswith("library/"):
            continue
        rec = json.loads(gzip.decompress((path / f["path"]).read_bytes()))
        m = rec["meta"]
        meta = {"title": m["title"], "heTitle": m.get("he_title"), "versionTitle": m["version_title"],
                "language": m.get("language", "he"), "license": m.get("license"), "versionSource": m.get("version_source"),
                "categories": m.get("categories"), "sectionNames": m.get("section_names"), "text": []}
        ok, dec, _ = library.import_version(con, meta, f"bundle:{bid[:16]}", m.get("sha256", ""), allow_tier_b)
        if ok:
            vid = con.execute("SELECT id FROM versions WHERE title=? AND version_title=? AND language=?",
                              (meta["title"], meta["versionTitle"], meta["language"])).fetchone()["id"]
            con.executemany("INSERT OR REPLACE INTO segments(version_id,ref,path,seq,text) VALUES (?,?,?,?,?)",
                            [(vid, r, p, s, t) for r, p, s, t in rec["segments"]])
            con.commit()
            stats["versions_imported"] += 1
        else:
            stats["versions_rejected"] += 1
    for ev in events:
        stats["events_new" if ledger.insert(con, ev, origin=f"bundle:{bid[:16]}") else "events_known"] += 1
    con.execute("INSERT INTO imported_bundles(id,authority,created,imported_at,events,versions) VALUES (?,?,?,?,?,?)",
                (bid, manifest["authority"], manifest["created"], ledger.now(), stats["events_new"], stats["versions_imported"]))
    con.commit()
    return {"bundle": bid, **stats}
