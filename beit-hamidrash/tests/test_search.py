from bhm import library
from bhm.features import search as S
from tests.conftest import SAMPLE


def test_norm():
    assert S.norm("בְּרֵאשִׁ֖ית־בָּרָ֣א, אֱלֹהִ֑ים") == "בראשית ברא אלהים"


def test_like_fallback_then_fts(fnode, client):
    r = client.get("/api/search/q", params={"q": "בראשית"}).json()
    assert r["mode"] == "like" and r["count"] >= 1
    assert client.get("/api/search/status").json()["indexed"] is False
    assert S.build_index(fnode.con) > 0
    r = client.get("/api/search/q", params={"q": "בראשית ברא"}).json()
    assert r["mode"] == "fts"
    assert r["results"][0]["ref"] == "Genesis 1:1"
    assert "⟦" in r["results"][0]["snippet"]
    st = client.get("/api/search/status").json()
    assert st["indexed"] and not st["stale"]


def test_filters_prefix_and_incremental(fnode, client):
    S.build_index(fnode.con)
    rs = client.get("/api/search/q", params={"q": "תהו", "book": "Rashi on Genesis"}).json()["results"]
    assert rs and all(x["book"] == "Rashi on Genesis" for x in rs)
    assert client.get("/api/search/q", params={"q": "תהו", "category": "Tanakh"}).json()["count"] >= 2
    assert client.get("/api/search/q", params={"q": "תהו", "category": "Talmud"}).json()["count"] == 0
    assert client.get("/api/search/q", params={"q": "ויכלו"}).json()["count"] == 1  # pointed text, plain query
    assert client.get("/api/search/q", params={"q": "השמ"}).json()["count"] == 1    # prefix
    meta = dict(SAMPLE, title="Exodus", versionTitle="X", text=[["שְׁמוֹת חדש"]])
    library.import_version(fnode.con, meta, "t", "h2")
    assert client.get("/api/search/status").json()["stale"] is True
    assert S.build_index(fnode.con) == 1
    assert client.get("/api/search/q", params={"q": "שמות"}).json()["count"] == 1


def test_limit_offset_and_empty(client, fnode):
    S.build_index(fnode.con)
    assert client.get("/api/search/q", params={"q": ""}).json()["results"] == []
    assert client.get("/api/search/q", params={"q": "אלהים", "limit": 1, "offset": 5}).json()["results"] == []
    assert client.get("/api/search/q", params={"q": 'a"b* OR'}).status_code == 200
