from bhm import ledger
from bhm.features import admin


def test_stats_basic(client, fnode):
    admin._cache.clear()
    fnode.trust("PUBKEYPUBKEYPUBKEYPUBKEY", "רשות")
    fnode.post("reuven", "commentary", {"text": "פירוש א"}, ref="Genesis 1:1")
    fnode.post("shimon", "commentary", {"text": "פירוש ב"}, ref="Genesis 1:2")
    s = client.get("/api/admin/stats", params={"refresh": True}).json()
    assert s["versions"] == 2 and s["versions_by_tier"]["certain"] == 2
    assert s["segments"] == 5 and s["books"] == 2
    assert s["events_by_kind"]["commentary"] == 2 and s["authors"] >= 3
    assert s["hidden"] == 0 and s["db_size_bytes"] > 0
    assert any(a["fingerprint"] == "PUBKEYPUBKEYPUBK" for a in s["trusted_authorities"])
    assert s["top_books_by_commentary"][0] == {"book": "Genesis", "he_title": "בראשית", "count": 2}
    assert s["imported_bundles"] == []


def test_cache_ttl_and_refresh(client, fnode):
    admin._cache.clear()
    a = client.get("/api/admin/stats").json()
    assert a["cached"] is False
    fnode.post("reuven", "commentary", {"text": "x"}, ref="Genesis 1:1")
    b = client.get("/api/admin/stats").json()
    assert b["cached"] is True and b["events"] == a["events"]
    c = client.get("/api/admin/stats?refresh=1").json()
    assert c["cached"] is False and c["events"] == a["events"] + 1


def test_hidden_and_legal(client, fnode):
    admin._cache.clear()
    ev = fnode.post("reuven", "commentary", {"text": "x"}, ref="Genesis 1:1")
    ledger.insert(fnode.con, ledger.make_event(fnode.identity("authority"), "hide", {}, target=ev["id"]))
    fnode.con.execute("INSERT INTO legal_log(at,origin,decision,reason) VALUES ('t','o','rejected','r')")
    fnode.con.commit()
    s = client.get("/api/admin/stats?refresh=1").json()
    assert s["hidden"] == 1 and s["legal_log"]["rejected"] == 1


def test_book_of():
    assert admin._book_of("Rashi on Genesis 1:1:2") == "Rashi on Genesis"


def test_stats_forbidden_remote(fnode):
    from fastapi.testclient import TestClient
    from bhm.api import create_app
    admin._cache.clear()
    c = TestClient(create_app(fnode), client=("8.8.8.8", 1))
    assert c.get("/api/admin/stats").status_code == 403
