import json

from bhm.features import toc

FAKE = [
    {"category": "Tanakh", "heCategory": "תנ\"ך", "contents": [
        {"category": "Torah", "heCategory": "תורה", "contents": [
            {"title": "Genesis", "heTitle": "בראשית", "order": 1},
            {"title": "Exodus", "heTitle": "שמות", "order": 2}]},
        {"category": "Empty", "heCategory": "ריק", "contents": [{"title": "Nothing", "heTitle": "כלום"}]}]},
]


def _titles(tree):
    out = []
    for n in tree:
        out += [n["book"]["title"]] if "book" in n else _titles(n["children"])
    return out


def test_fallback_without_cache(client):
    d = client.get("/api/toc").json()
    assert d["source"] == "fallback"
    assert sorted(_titles(d["tree"])) == ["Genesis", "Rashi on Genesis"]
    assert d["tree"][0]["he"] == "תנ\"ך"


def test_cache_restricted_to_library(client, fnode):
    (fnode.home / "toc_cache.json").write_text(json.dumps(FAKE, ensure_ascii=False), encoding="utf-8")
    d = client.get("/api/toc").json()
    assert d["source"] == "cache"
    t = _titles(d["tree"])
    assert "Genesis" in t and "Exodus" not in t and "Nothing" not in t
    assert "Rashi on Genesis" in t  # absent from toc, still listed
    assert not any(n.get("category") == "Empty" for n in d["tree"][0]["children"])
    assert d["tree"][0]["he"] == "תנ\"ך"


def test_refresh_uses_fetch_and_offline_ok(client, fnode, monkeypatch):
    monkeypatch.setattr(toc, "fetch_toc", lambda node, url=None: (_ for _ in ()).throw(OSError("offline")))
    assert client.post("/api/toc/refresh").status_code == 502
    d = client.get("/api/toc?refresh=1").json()
    assert d["source"] == "fallback" and d["warning"]

    def ok(node, url=None):
        (node.home / "toc_cache.json").write_text(json.dumps(FAKE))
        return FAKE
    monkeypatch.setattr(toc, "fetch_toc", ok)
    d = client.get("/api/toc?refresh=1").json()
    assert d["source"] == "cache" and d["warning"] is None


def test_corrupt_cache_falls_back(client, fnode):
    (fnode.home / "toc_cache.json").write_text("{not json")
    assert client.get("/api/toc").json()["source"] == "fallback"
