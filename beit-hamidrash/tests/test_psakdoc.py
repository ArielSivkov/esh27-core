import pathlib
from datetime import date

from bhm import beitdin
from bhm.features import psakdoc


def _draft(fnode, **kw):
    body = {"question": "שאלה <b>x</b>", "answer": "תשובה", "sources": ["Genesis 1:1", "Nope 9:9"], **kw}
    return fnode.post("reuven", "psak_draft", body)


def test_unsigned_has_notices(fnode, client):
    d = _draft(fnode, ai_generated=True)
    r = client.get(f"/api/psakdoc/{d['id']}")
    assert r.status_code == 200
    j = r.json()
    assert beitdin.DRAFT_NOTICE in j["notices"] and beitdin.AI_NOTICE in j["notices"]
    assert j["watermark"] == "טיוטה" and j["status"] == "draft"
    assert j["file_number"] == d["id"][:8] and j["header"]["blessing"] == 'בס"ד'
    assert j["sources"][0]["found"] and "בְּרֵאשִׁית" in j["sources"][0]["versions"][0]["text"]
    assert not j["sources"][1]["found"]
    assert j["signatures"] == []


def test_non_dayan_signature_ignored(fnode, client):
    d = _draft(fnode)
    fnode.post("shimon", "psak_sign", {"decision": "approved"}, target=d["id"])
    j = client.get(f"/api/psakdoc/{d['id']}").json()
    assert beitdin.DRAFT_NOTICE in j["notices"] and j["signatures"] == [] and not j["approved"]


def test_approved_no_notice(fnode, client):
    d = _draft(fnode)
    fnode.post("authority", "grant_role", {"subject": fnode.identity("shimon").pubkey, "role": "dayan"})
    fnode.post("shimon", "psak_sign", {"decision": "approved", "note": "ok"}, target=d["id"])
    j = client.get(f"/api/psakdoc/{d['id']}").json()
    assert j["approved"] and j["notices"] == [] and j["watermark"] is None
    assert len(j["signatures"]) == 1 and j["signatures"][0]["by"] == "שמעון"


def test_beit_din_name_env_and_404(fnode, client, monkeypatch):
    d = _draft(fnode)
    monkeypatch.setenv("BHM_BEITDIN_NAME", "בית דין צדק")
    assert client.get(f"/api/psakdoc/{d['id']}").json()["header"]["beit_din"] == "בית דין צדק"
    assert client.get("/api/psakdoc/deadbeef").status_code == 404


def test_hebrew_date():
    assert psakdoc.hebrew_date(date(2026, 9, 12)) == (5787, "תשרי", 1)
    assert psakdoc.hebrew_date(date(2026, 4, 2)) == (5786, "ניסן", 15)
    assert psakdoc.hebrew_date(date(2024, 3, 24)) == (5784, "אדר ב׳", 14)
    assert psakdoc.hebrew_date_str(date(2026, 4, 2)) == "ט״ו ניסן תשפ״ו"


def test_js_escapes_and_print():
    js = (pathlib.Path(__file__).parent.parent / "web/features/psakdoc.js").read_text()
    assert "esc(d.question)" in js and "esc(d.answer)" in js and "@media print" in js


def test_malformed_sources_no_500(fnode, client):
    for bad in ("Genesis 1:1", {"a": 1}, [1, None, ["x"], "x" * 101, "100%_"], ["Genesis 1:1"] * 30):
        d = fnode.post("reuven", "psak_draft", {"question": "q", "answer": "a", "sources": bad})
        r = client.get(f"/api/psakdoc/{d['id']}")
        assert r.status_code == 200
        assert len(r.json()["sources"]) <= 20
    d = fnode.post("reuven", "psak_draft", {"question": "q", "answer": "a", "sources": ["%"]})
    assert not client.get(f"/api/psakdoc/{d['id']}").json()["sources"][0]["found"]
