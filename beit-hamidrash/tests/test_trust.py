import json
from datetime import datetime, timedelta, timezone

import pytest

from bhm.features import trust
from bhm.signing import Identity

FUT = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
PAST = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def ids(n):
    return [Identity.generate() for _ in range(n)]


def root(version, root_ids, thr, bundle_ids=(), expires=FUT):
    allk = [i.pubkey for i in list(root_ids) + list(bundle_ids)]
    roles = {"root": {"keys": [i.pubkey for i in root_ids], "threshold": thr}}
    if bundle_ids:
        roles["bundles"] = {"keys": [i.pubkey for i in bundle_ids], "threshold": 1}
    return trust.make_root(version, expires, allk, roles)


def test_threshold_met_and_not():
    a = ids(3)
    s = root(1, a, 2)
    assert trust.verify_root(trust.sign_root(s, a[:2]), None)["version"] == 1
    with pytest.raises(trust.TrustError):
        trust.verify_root(trust.sign_root(s, a[:1]), None)


def test_duplicate_signature_not_double_counted():
    a = ids(3)
    r = trust.sign_root(root(1, a, 2), [a[0]])
    r["signatures"] = r["signatures"] * 2
    with pytest.raises(trust.TrustError):
        trust.verify_root(r, None)


def test_tamper_detected():
    a = ids(2)
    r = trust.sign_root(root(1, a, 2), a)
    r["signed"]["version"] = 5
    with pytest.raises(trust.TrustError):
        trust.verify_root(r, None)


def test_unknown_signer_ignored():
    a, x = ids(3), ids(1)
    r = trust.sign_root(root(1, a, 2), [a[0], x[0]])
    with pytest.raises(trust.TrustError):
        trust.verify_root(r, None)


def test_expired():
    a = ids(2)
    r = trust.sign_root(root(1, a, 2, expires=PAST), a)
    with pytest.raises(trust.TrustError, match="expired"):
        trust.verify_root(r, None)


def test_rotation_needs_both_old_and_new():
    old, new = ids(3), ids(3)
    r1 = trust.sign_root(root(1, old, 2), old[:2])
    s2 = root(2, new, 2)
    good = trust.sign_root(s2, old[:2] + new[:2])
    assert trust.verify_root(good, r1)["version"] == 2
    with pytest.raises(trust.TrustError, match="old root"):
        trust.verify_root(trust.sign_root(s2, old[:1] + new[:2]), r1)
    with pytest.raises(trust.TrustError, match="new root"):
        trust.verify_root(trust.sign_root(s2, old[:2] + new[:1]), r1)
    with pytest.raises(trust.TrustError):
        trust.verify_root(trust.sign_root(s2, new[:2]), r1)


def test_rollback_and_skip():
    a = ids(2)
    r2 = trust.sign_root(root(2, a, 2), a)
    for v in (1, 2, 4):
        with pytest.raises(trust.TrustError, match="rollback"):
            trust.verify_root(trust.sign_root(root(v, a, 2), a), r2)
    assert trust.verify_root(trust.sign_root(root(3, a, 2), a), r2)["version"] == 3


def test_bad_structure():
    a = ids(2)
    with pytest.raises(trust.TrustError):
        trust.verify_root(trust.sign_root(root(1, a, 3), a), None)
    with pytest.raises(trust.TrustError):
        trust.verify_root({}, None)


def test_role_signature():
    r, b = ids(2), ids(2)
    meta = trust.sign_root(root(1, r, 2, bundle_ids=b), r)
    payload = {"manifest": "abc"}
    sig = [{"keyid": trust.keyid(b[0].pubkey), "sig": b[0].sign(trust.canonical(payload))}]
    assert trust.verify_role_signature(meta, "bundles", payload, sig)
    assert not trust.verify_role_signature(meta, "bundles", {"manifest": "x"}, sig)
    assert not trust.verify_role_signature(meta, "nope", payload, sig)
    assert not trust.verify_role_signature(meta, "bundles", payload, [])
    bad = [{"keyid": trust.keyid(r[0].pubkey), "sig": r[0].sign(trust.canonical(payload))}]
    assert not trust.verify_role_signature(meta, "bundles", payload, bad)


def test_role_signature_expired_root():
    r = ids(1)
    meta = trust.sign_root(root(1, r, 1, expires=PAST), r)
    p = {"a": 1}
    sig = [{"keyid": trust.keyid(r[0].pubkey), "sig": r[0].sign(trust.canonical(p))}]
    assert not trust.verify_role_signature(meta, "root", p, sig)


def test_api_info(fnode, client):
    assert client.get("/api/trust/info").json() == {"present": False}
    a = ids(2)
    (fnode.home / "root.json").write_text(json.dumps(trust.sign_root(root(3, a, 2), a)))
    d = client.get("/api/trust/info").json()
    assert d["present"] and d["version"] == 3 and d["self_signed_ok"] and not d["expired"]
    assert d["roles"]["root"]["threshold"] == 2
    (fnode.home / "root.json").write_text("{bad")
    assert client.get("/api/trust/info").json()["present"] is False
