"""TUF-style trust metadata (module; not wired into bundle.py).

Root metadata (the "signed" part):
    {"_type": "root", "version": int, "expires": ISO-8601 UTC,
     "keys":  {keyid: base64-ed25519-pubkey},
     "roles": {"root": {"keyids": [...], "threshold": n},
               "bundles": {...}, "roles": {...}}}
A signed root file is {"signed": <above>, "signatures": [{"keyid", "sig"}]}.
keyid = signing.fingerprint(pubkey). Signatures are over canonical JSON.

Rotation: a new root is accepted only if it is signed by a threshold of the
OLD root's root keys AND a threshold of its OWN root keys, its version is exactly
old+1 (rollback/freeze protection) and it is not expired.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter

from ..signing import Identity, canonical, fingerprint, verify

NAV = {"label": "אמון", "href": "#/trust"}
ROOT_FILE = "root.json"


class TrustError(ValueError):
    pass


def keyid(pubkey: str) -> str:
    return fingerprint(pubkey)


def _now(now):
    return now or datetime.now(timezone.utc)


def _parse_time(s) -> datetime:
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError, OverflowError) as e:
        raise TrustError("bad expires") from e
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def make_root(version: int, expires: str, keys: list[str], roles: dict) -> dict:
    """Build unsigned root. `roles` maps role -> {"keys": [pubkeys], "threshold": n}."""
    kmap = {keyid(k): k for k in keys}
    r = {name: {"keyids": sorted(keyid(k) for k in spec["keys"]), "threshold": spec["threshold"]}
         for name, spec in roles.items()}
    return {"_type": "root", "version": version, "expires": expires, "keys": kmap, "roles": r}


def sign_root(signed: dict, identities: list[Identity]) -> dict:
    data = canonical(signed)
    sigs = [{"keyid": keyid(i.pubkey), "sig": i.sign(data)} for i in identities]
    return {"signed": signed, "signatures": sigs}


def _count_valid(signed_bytes: bytes, sigs, keys: dict, role: dict) -> int:
    if not isinstance(sigs, list) or not isinstance(keys, dict) or not isinstance(role, dict):
        return 0
    ids = role.get("keyids")
    allowed = {i for i in ids if isinstance(i, str)} if isinstance(ids, list) else set()
    seen = set()
    for s in sigs:
        if not isinstance(s, dict):
            continue
        kid, sig = s.get("keyid"), s.get("sig")
        if not isinstance(kid, str) or not isinstance(sig, str):
            continue
        if kid in allowed and kid not in seen and isinstance(keys.get(kid), str):
            try:
                ok = verify(keys[kid], signed_bytes, sig)
            except Exception:
                ok = False
            if ok:
                seen.add(kid)
    return len(seen)


def _check_structure(signed: dict) -> None:
    if not isinstance(signed, dict) or signed.get("_type") != "root":
        raise TrustError("not a root")
    if not isinstance(signed.get("version"), int) or signed["version"] < 1:
        raise TrustError("bad version")
    keys, roles = signed.get("keys"), signed.get("roles")
    if not isinstance(keys, dict) or not isinstance(roles, dict) or "root" not in roles:
        raise TrustError("missing keys/roles.root")
    for kid, pk in keys.items():
        if not isinstance(kid, str) or not isinstance(pk, str):
            raise TrustError("keys must map str -> str")
        try:
            ok = keyid(pk) == kid
        except Exception:
            ok = False
        if not ok:
            raise TrustError("keyid does not match key")
    for name, r in roles.items():
        if not isinstance(name, str) or not isinstance(r, dict):
            raise TrustError(f"bad role {name}")
        ids, t = r.get("keyids"), r.get("threshold")
        if (not isinstance(ids, list) or not all(isinstance(i, str) for i in ids)
                or not isinstance(t, int) or isinstance(t, bool) or t < 1):
            raise TrustError(f"bad role {name}")
        if len(set(ids)) < t or any(i not in keys for i in ids):
            raise TrustError(f"role {name}: threshold unreachable or unknown key")


def verify_root(new_root: dict, trusted_root: dict | None, now=None) -> dict:
    """Verify `new_root` against `trusted_root`; return its signed part.

    trusted_root None = bootstrap (self-signed only); use only for a root
    obtained out of band.
    """
    if not isinstance(new_root, dict):
        raise TrustError("root must be an object")
    signed = new_root.get("signed")
    sigs = new_root.get("signatures")
    if not isinstance(sigs, list):
        raise TrustError("signatures must be a list")
    _check_structure(signed)
    if _parse_time(signed["expires"]) <= _now(now):
        raise TrustError("new root expired")
    need = signed["roles"]["root"]["threshold"]
    got = _count_valid(canonical(signed), sigs, signed["keys"], signed["roles"]["root"])
    if got < need:
        raise TrustError(f"new root: {got}/{need} valid root signatures")
    if trusted_root is not None:
        if not isinstance(trusted_root, dict):
            raise TrustError("bad trusted root")
        old = trusted_root.get("signed")
        _check_structure(old)
        if signed["version"] != old["version"] + 1:
            raise TrustError(f"version {signed['version']} is not {old['version']}+1 (rollback/skip)")
        need = old["roles"]["root"]["threshold"]
        got = _count_valid(canonical(signed), sigs, old["keys"], old["roles"]["root"])
        if got < need:
            raise TrustError(f"old root threshold not met: {got}/{need}")
    return signed


def verify_role_signature(meta: dict, role: str, payload, sigs, now=None) -> bool:
    """True iff `sigs` hold a threshold of valid signatures over canonical(payload)
    by the role's keys in trusted root `meta` (signed part or full file)."""
    if not isinstance(meta, dict):
        return False
    signed = meta.get("signed", meta)
    try:
        _check_structure(signed)
        if _parse_time(signed["expires"]) <= _now(now):
            return False
    except TrustError:
        return False
    r = signed["roles"].get(role)
    if not r:
        return False
    try:
        return _count_valid(canonical(payload), sigs, signed["keys"], r) >= r["threshold"]
    except (TypeError, ValueError):
        return False


def load_root(node) -> dict | None:
    p = node.home / ROOT_FILE
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _roles_summary(roles) -> dict:
    out = {}
    if not isinstance(roles, dict):
        return out
    for n, r in roles.items():
        if not isinstance(r, dict):
            continue
        ids = r.get("keyids")
        ids = [i for i in ids if isinstance(i, str)] if isinstance(ids, list) else []
        out[str(n)] = {"threshold": r.get("threshold"), "keys": len(ids), "keyids": ids}
    return out


def summarize(root: dict, now=None) -> dict:
    if not isinstance(root, dict):
        root = {}
    s = root.get("signed", {})
    if not isinstance(s, dict):
        s = {}
    exp = s.get("expires")
    try:
        expired = _parse_time(exp) <= _now(now)
    except TrustError:
        expired = True
    try:
        _check_structure(s)
        got = _count_valid(canonical(s), root.get("signatures"), s["keys"], s["roles"]["root"])
        self_ok = got >= s["roles"]["root"]["threshold"]
    except TrustError:
        self_ok = False
    return {"present": True, "version": s.get("version"), "expires": exp, "expired": expired,
            "self_signed_ok": self_ok,
            "roles": _roles_summary(s.get("roles")),
            "keys": len(s["keys"]) if isinstance(s.get("keys"), dict) else 0}


def make_router(node) -> APIRouter:
    r = APIRouter()

    @r.get("/api/trust/info")
    def info():
        try:
            root = load_root(node)
        except (ValueError, OSError):
            return {"present": False, "error": "root.json unreadable"}
        if root is None:
            return {"present": False}
        return summarize(root)

    return r
