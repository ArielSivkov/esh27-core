import json
import shutil

import pytest

from bhm import beitdin, bundle, legal, ledger, library
from bhm.node import Node
from bhm.signing import Identity

GEN = {"title": "Genesis", "heTitle": "בראשית", "versionTitle": "Test PD", "language": "he",
       "license": "Public Domain", "categories": ["Tanakh", "Torah"], "sectionNames": ["Chapter", "Verse"],
       "text": [["בראשית ברא אלהים", "והארץ היתה תהו ובהו"], ["ויכלו השמים"]]}


@pytest.fixture
def node(tmp_path):
    n = Node(tmp_path / "a")
    n.init_authority()
    return n


# ---------------------------------------------------------------- legal
@pytest.mark.parametrize("lic,tier", [
    ("Public Domain", legal.TIER_A), ("PD", legal.TIER_A), ("CC0", legal.TIER_A),
    ("CC-BY", legal.TIER_B), ("CC-BY-SA", legal.TIER_B), ("CC-BY-NC", legal.REJECT),
    ("CC-BY-NC-SA", legal.REJECT), ("unknown", legal.REJECT), (None, legal.REJECT), ("Copyright", legal.REJECT),
])
def test_license_classes(lic, tier):
    assert legal.classify(lic).tier == tier


def test_modern_pd_needs_manual_review():
    d = legal.review({"title": "Genesis", "versionTitle": "Miqra Mevoar, Jerusalem 2020", "license": "PD"})
    assert not d.allowed and "אימות ידני" in d.reason
    assert legal.review({"title": "X", "versionTitle": "Warsaw 1884", "license": "Public Domain"}).allowed


def test_tier_b_off_by_switch():
    assert not legal.review({"license": "CC-BY-SA", "versionTitle": "x"}, allow_tier_b=False).allowed
    assert legal.review({"license": "CC-BY-SA", "versionTitle": "x"}, allow_tier_b=True).allowed


def test_import_and_reject(node):
    ok, _, n = library.import_version(node.con, GEN, "test", "h")
    assert ok and n == 3
    vid = library.versions_of(node.con, "Genesis")[0]["id"]
    assert [s["ref"] for s in library.chapter(node.con, vid, "Genesis 1")] == ["Genesis 1:1", "Genesis 1:2"]
    bad = dict(GEN, versionTitle="Kaplan", license="unknown")
    ok, dec, _ = library.import_version(node.con, bad, "test", "h")
    assert not ok and dec.tier == legal.REJECT
    assert node.con.execute("SELECT COUNT(*) FROM legal_log WHERE decision='rejected'").fetchone()[0] == 1


# ---------------------------------------------------------------- ledger
def test_signed_event_roundtrip(node):
    node.create_user("reuven")
    ev = node.post("reuven", "commentary", {"text": "פירוש"}, ref="Genesis 1:1")
    ledger.check_event(ev)
    tampered = json.loads(json.dumps(ev))
    tampered["body"]["text"] = "פירוש אחר"
    with pytest.raises(ledger.LedgerError):
        ledger.check_event(tampered)


def test_roles_only_from_authority(node):
    node.create_user("reuven"); node.create_user("shimon")
    rk = node.identity("reuven").pubkey
    node.post("shimon", "grant_role", {"subject": rk, "role": "dayan"})          # not an authority: ignored
    assert "dayan" not in ledger.roles(node.con).get(rk, set())
    node.post("authority", "grant_role", {"subject": rk, "role": "dayan"})
    assert "dayan" in ledger.roles(node.con)[rk]


def test_hide_keeps_history(node):
    node.create_user("reuven")
    ev = node.post("reuven", "commentary", {"text": "x"}, ref="Genesis 1:1")
    node.post("authority", "hide", {"reason": "test"}, target=ev["id"])
    assert ev["id"] in ledger.hidden(node.con)
    assert node.con.execute("SELECT COUNT(*) FROM events WHERE id=?", (ev["id"],)).fetchone()[0] == 1


# ---------------------------------------------------------------- beit din
def test_draft_needs_dayan_signature(node):
    node.create_user("talmid"); node.create_user("dayan")
    d = node.post("talmid", "psak_draft", {"question": "שאלה", "answer": "תשובה", "sources": ["Genesis 1:1"], "ai_generated": True})
    st = beitdin.draft_status(node.con, d["id"])
    assert st["status"] == "draft" and beitdin.DRAFT_NOTICE in st["notices"] and beitdin.AI_NOTICE in st["notices"]
    node.post("talmid", "psak_sign", {"decision": "approved"}, target=d["id"])  # not a dayan
    st = beitdin.draft_status(node.con, d["id"])
    assert st["status"] == "draft" and len(st["ignored_signatures"]) == 1
    node.post("talmid", "psak_review", {"note": "צריך עיון"}, target=d["id"])
    assert beitdin.draft_status(node.con, d["id"])["status"] == "in_review"
    node.post("authority", "grant_role", {"subject": node.identity("dayan").pubkey, "role": "dayan"})
    node.post("dayan", "psak_sign", {"decision": "approved", "note": "מסכים"}, target=d["id"])
    st = beitdin.draft_status(node.con, d["id"])
    assert st["status"] == "approved" and beitdin.DRAFT_NOTICE not in st["notices"]


def test_draft_requires_sources(node):
    node.create_user("talmid")
    with pytest.raises(ledger.LedgerError):
        node.post("talmid", "psak_draft", {"question": "q", "answer": "a", "sources": []})


# ---------------------------------------------------------------- USB bundles
def _make_bundle(node, tmp_path):
    library.import_version(node.con, GEN, "test", "h")
    node.create_user("reuven")
    node.post("reuven", "commentary", {"text": "פירוש"}, ref="Genesis 1:1")
    out = tmp_path / "usb"
    bundle.export_bundle(node.con, node.identity("authority"), out)
    return out


def test_bundle_roundtrip(node, tmp_path):
    out = _make_bundle(node, tmp_path)
    other = Node(tmp_path / "b")
    other.trust(node.identity("authority").pubkey, "central")
    res = bundle.import_bundle(other.con, out)
    assert res["versions_imported"] == 1 and res["events_new"] >= 3
    assert bundle.import_bundle(other.con, out)["status"] == "already imported"
    vid = library.versions_of(other.con, "Genesis")[0]["id"]
    assert library.chapter(other.con, vid, "Genesis 2")[0]["text"] == "ויכלו השמים"


def test_bundle_untrusted_authority(node, tmp_path):
    out = _make_bundle(node, tmp_path)
    with pytest.raises(bundle.BundleError, match="does not trust"):
        bundle.verify_bundle(Node(tmp_path / "b").con, out)


@pytest.mark.parametrize("attack", ["tamper", "extra_file", "exe", "symlink"])
def test_bundle_attacks(node, tmp_path, attack):
    out = _make_bundle(node, tmp_path)
    other = Node(tmp_path / "b")
    other.trust(node.identity("authority").pubkey, "central")
    if attack == "tamper":
        p = out / "events.jsonl"
        p.write_bytes(p.read_bytes().replace("פירוש".encode(), "זיוף!".encode()))
    elif attack == "extra_file":
        (out / "library" / "evil.jsonl").write_text("{}")
    elif attack == "exe":
        (out / "autorun.exe").write_bytes(b"MZ")
    elif attack == "symlink":
        (out / "link.jsonl").symlink_to("/etc/passwd")
    with pytest.raises(bundle.BundleError):
        bundle.import_bundle(other.con, out)
    assert other.con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_bundle_receiver_applies_own_legal_policy(node, tmp_path):
    library.import_version(node.con, dict(GEN, versionTitle="MAM", license="CC-BY-SA"), "t", "h", allow_tier_b=True)
    out = tmp_path / "usb"
    bundle.export_bundle(node.con, node.identity("authority"), out)
    other = Node(tmp_path / "b")
    other.trust(node.identity("authority").pubkey, "central")
    res = bundle.import_bundle(other.con, out, allow_tier_b=False)
    assert res["versions_rejected"] == 1 and res["versions_imported"] == 0


def test_forged_authority_signature(node, tmp_path):
    out = _make_bundle(node, tmp_path)
    other = Node(tmp_path / "b")
    other.trust(node.identity("authority").pubkey, "central")
    (out / "manifest.sig").write_text(Identity.generate().sign(b"x"))
    with pytest.raises(bundle.BundleError, match="signature"):
        bundle.verify_bundle(other.con, out)
