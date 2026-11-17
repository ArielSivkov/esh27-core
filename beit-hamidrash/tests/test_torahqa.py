from bhm import library
from bhm.features import torahqa
from conftest import SAMPLE


def test_count_text():
    assert torahqa.count_text("בְּרֵאשִׁית בָּרָא") == (9, 2)
    assert torahqa.count_text("אֶרֶץ־בֹּו [הערה] (x) {פ}") == (5, 2)
    assert torahqa.count_text("<b>שלום</b> ך") == (5, 2)


def test_api_report(client, fnode):
    r = client.get("/api/torahqa").json()
    g = r["books"][0]
    assert g["title"] == "Genesis" and len(g["versions"]) == 1
    v = g["versions"][0]
    assert v["verses"] == 3 and v["chapters"] == 2
    assert v["letters"] == sum(torahqa.count_text(t)[0] for ch in SAMPLE["text"] for t in ch)
    assert v["delta_verses"] == 3 - 1534
    assert r["std"] == {"letters": 304805, "verses": 5845}
    assert sum(torahqa.STD_LETTERS.values()) == 304805 and sum(torahqa.STD_VERSES.values()) == 5845
    assert r["totals"] == [] and r["cached"] is False
    assert client.get("/api/torahqa").json()["cached"] is True
    assert client.get("/api/torahqa?refresh=true").json()["cached"] is False


def test_cache_invalidates_on_import(client, fnode):
    client.get("/api/torahqa")
    other = dict(SAMPLE, versionTitle="Other PD", text=[["אב"]])
    library.import_version(fnode.con, other, "test", "h")
    r = client.get("/api/torahqa").json()
    assert r["cached"] is False and len(r["books"][0]["versions"]) == 2
