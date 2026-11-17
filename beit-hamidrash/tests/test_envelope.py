import copy

import pytest

from bhm.features import envelope as E
from bhm.features import load_features
from bhm.ledger import LedgerError, check_event, make_event
from bhm.signing import Identity, canonical, sha256_hex

BODY = {"text": "דברי תורה", "n": 1}


@pytest.fixture
def ident():
    return Identity.generate()


def test_signed_payload_has_hash_not_body(ident):
    ev = E.make_event_v2(ident, "article", {"title": "t", "text": "x"})
    assert ev["v"] == 2 and ev["body_hash"] == E.body_hash(ev["body"])
    signed = {k: ev[k] for k in E.SIGNED_FIELDS}
    assert "body" not in signed and sha256_hex(canonical(signed)) == ev["id"]


def test_hash_is_canonical():
    assert E.body_hash({"a": 1, "b": 2}) == E.body_hash({"b": 2, "a": 1})
    assert E.body_hash({"a": 1}) != E.body_hash({"a": 2})


def test_verify_with_blob_without_blob(ident):
    ev = E.make_event_v2(ident, "reply", BODY, target="x" * 8)
    assert E.verify_v2(ev, ev["body"]) and E.verify_v2(ev, None)
    assert E.verify_v2(E.strip_body(ev))


def test_wrong_blob_rejected(ident):
    ev = E.make_event_v2(ident, "article", BODY)
    assert not E.verify_v2(ev, {"text": "other"})
    assert not E.verify_v2(ev, "nope")


@pytest.mark.parametrize("field,val", [("kind", "reply"), ("ts", "2020-01-01T00:00:00+00:00"),
                                       ("ref", "Genesis 1:1"), ("target", "abc"),
                                       ("body_hash", "0" * 64), ("author", "AAAA")])
def test_tamper_breaks(ident, field, val):
    ev = E.make_event_v2(ident, "article", BODY)
    assert not E.verify_v2({**ev, field: val}, None)


def test_bad_sig_id_and_version(ident):
    ev = E.make_event_v2(ident, "article", BODY)
    other = Identity.generate()
    assert not E.verify_v2({**ev, "sig": other.sign(b"x")})
    assert not E.verify_v2({**ev, "id": "0" * 64})
    assert not E.verify_v2({**ev, "v": 1})
    assert not E.verify_v2({k: v for k, v in ev.items() if k != "sig"})
    assert not E.verify_v2({**ev, "kind": "nonsense"})
    assert not E.verify_v2({**ev, "body_hash": "XYZ"})
    assert not E.verify_v2(None)


def test_forged_body_detected_only_via_blob(ident):
    ev = E.make_event_v2(ident, "article", BODY)
    ev2 = {**ev, "body": {"text": "forged"}}
    assert E.verify_v2(ev2, None)
    assert not E.verify_v2(ev2, ev2["body"])


def test_no_collision_with_v1(ident):
    v1 = make_event(ident, "article", BODY, ts="2024-01-01T00:00:00+00:00")
    v2 = E.make_event_v2(ident, "article", BODY, ts="2024-01-01T00:00:00+00:00")
    assert v1["id"] != v2["id"]
    with pytest.raises(LedgerError):
        check_event(E.strip_body(v2))
    assert not E.verify_v2(v1)


def test_too_large_and_bad_body(ident):
    with pytest.raises(LedgerError):
        E.make_event_v2(ident, "article", {"text": "א" * 70000})
    with pytest.raises(LedgerError):
        E.make_event_v2(ident, "article", "str")


def test_blob_store_put_get(fnode):
    bs = E.BlobStore(fnode.con)
    h = bs.put(BODY)
    assert h == E.body_hash(BODY) and bs.get(h) == BODY and bs.has(h)
    assert bs.put(BODY) == h and bs.stats() == {"blobs": 1, "purged": 0}
    assert bs.get("f" * 64) is None


def test_purge_keeps_hash_and_event_valid(fnode, ident):
    bs = E.BlobStore(fnode.con)
    ev = E.make_event_v2(ident, "article", BODY)
    bs.put(ev["body"])
    assert bs.purge(ev["body_hash"], "illegal") is True
    assert bs.get(ev["body_hash"]) is None and bs.is_purged(ev["body_hash"])
    row = fnode.con.execute("SELECT hash,body,purged FROM envelope_blobs").fetchone()
    assert row[0] == ev["body_hash"] and row[1] is None and row[2] == 1
    assert E.verify_v2(E.strip_body(ev), bs.get(ev["body_hash"]))
    assert bs.purge(ev["body_hash"]) is False


def test_purged_not_resurrected(fnode):
    bs = E.BlobStore(fnode.con)
    h = bs.put(BODY)
    bs.purge(h)
    assert bs.put(BODY) == h and bs.get(h) is None


def test_purge_unknown_hash_tombstones(fnode):
    bs = E.BlobStore(fnode.con)
    h = E.body_hash(BODY)
    assert bs.purge(h) and bs.put(BODY) == h and bs.get(h) is None
    with pytest.raises(LedgerError):
        bs.purge("short")


def test_corrupt_stored_blob_not_returned(fnode):
    bs = E.BlobStore(fnode.con)
    h = bs.put(BODY)
    fnode.con.execute("UPDATE envelope_blobs SET body='{\"text\":\"evil\"}' WHERE hash=?", (h,))
    assert bs.get(h) is None


def test_convert_v1_to_v2(ident):
    v1 = make_event(ident, "article", {"title": "t", "text": "x"})
    snap = copy.deepcopy(v1)
    out = E.convert_v1_to_v2(v1)
    assert v1 == snap and out["legacy"] == v1
    check_event(out["legacy"])
    assert out["body_hash"] == E.body_hash(v1["body"]) and out["blob"] == v1["body"]
    assert "re-sign" in out["note"]
    with pytest.raises(LedgerError):
        E.convert_v1_to_v2({"body": "x"})


def test_info_route(client):
    r = client.get("/api/envelope/info")
    assert r.status_code == 200
    j = r.json()
    assert j["protocol"] == 2 and j["wired_into_core"] is False and "body_hash" in j["signed_fields"]


def test_only_info_route():
    assert {r.path for r in E.make_router(None).routes} == {"/api/envelope/info"}


def test_feature_loaded():
    assert "envelope" in [f.name for f in load_features()]


@pytest.mark.parametrize("kind", ["reply", "endorse", "hide", "unhide", "psak_review", "psak_sign", "report", "edit"])
def test_v2_target_required(ident, kind):
    ev = E.make_event_v2(ident, kind, {"text": "x", "decision": "approved"})
    with pytest.raises(LedgerError):
        E.check_event_v2(ev)
    assert not E.verify_v2(ev)


def test_v2_commentary_requires_ref(ident):
    ev = E.make_event_v2(ident, "commentary", {"text": "x"})
    assert not E.verify_v2(ev)
    assert E.verify_v2(E.make_event_v2(ident, "commentary", {"text": "x"}, ref="r"), {"text": "x"})


def test_v2_body_rules_with_blob(ident):
    ev = E.make_event_v2(ident, "article", {"title": "", "text": "x"})
    assert E.verify_v2(ev)  # envelope alone
    assert not E.verify_v2(ev, ev["body"])
    ev = E.make_event_v2(ident, "follow", {})
    assert not E.verify_v2(ev, {})
    ev = E.make_event_v2(ident, "psak_sign", {"decision": "maybe"}, target="t")
    assert not E.verify_v2(ev, ev["body"])
    ev = E.make_event_v2(ident, "article", {"title": "t", "text": "x"})
    assert E.verify_v2(ev, ev["body"])


def test_blobstore_put_enforces_max_size():
    import sqlite3
    from bhm.ledger import MAX_BODY_BYTES
    st = E.BlobStore(sqlite3.connect(":memory:"))
    with pytest.raises(LedgerError):
        st.put({"text": "x" * (MAX_BODY_BYTES + 1)})
    with pytest.raises(LedgerError):
        st.put("notadict")
    assert st.stats()["blobs"] == 0
