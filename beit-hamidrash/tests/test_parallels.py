def test_parallels_verse(client):
    d = client.get("/api/parallels", params={"ref": "Genesis 1:1"}).json()
    assert d["base"]["text"].startswith("בְּרֵאשִׁית")
    c = d["commentaries"]
    assert [x["title"] for x in c] == ["Rashi on Genesis"]
    assert c[0]["license"] == "Public Domain" and c[0]["segments"][0]["ref"] == "Rashi on Genesis 1:1:1"
    assert c[0]["segments"][0]["text"].startswith("בראשית")


def test_parallels_second_verse_and_none(client):
    d = client.get("/api/parallels", params={"ref": "Genesis 1:2"}).json()
    assert d["commentaries"][0]["segments"][0]["text"].startswith("תהו")
    assert client.get("/api/parallels", params={"ref": "Genesis 2:1"}).json()["commentaries"] == []


def test_parallels_bad_ref(client):
    assert client.get("/api/parallels", params={"ref": "Genesis"}).status_code == 400
    assert client.get("/api/parallels/count", params={"chapter": "x"}).status_code == 400


def test_parallels_count(client):
    d = client.get("/api/parallels/count", params={"chapter": "Genesis 1"}).json()
    assert d["counts"] == {"1": 1, "2": 1} and d["commentators"]["1"] == 1
