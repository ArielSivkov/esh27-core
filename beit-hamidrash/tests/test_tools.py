from bhm.features import tools as T


def test_values():
    assert T.gematria("אהבה") == 13 and T.gematria("אחד") == 13
    assert T.gematria("יהוה") == 26 and T.gematria("שלום") == 376
    assert T.gematria("בְּרֵאשִׁית") == 913
    assert T.gematria("שלום", "big") == 376 - 40 + 600
    assert T.gematria("אבג", "ordinal") == 6 and T.gematria("תק", "small") == 5
    assert T.gematria("אחד", "kolel") == 16


def test_milui():
    assert T.milui_of_name() == {'ע"ב': 72, 'ס"ג': 63, 'מ"ה': 45, 'ב"ן': 52}
    assert T.gematria("יהוה", "milui") == 45


def test_atbash_albam_gates():
    assert T.atbash("בבל") == "ששכ"
    assert T.albam("א") == "ל" and T.atbash("א") == "ת"
    g = T.gates()
    assert len(g) == 231 and len({x["gate"] for x in g}) == 231


def test_api(client):
    d = client.get("/api/tools/gematria", params={"ref": "Genesis 1:1"}).json()
    assert d["segments"][0]["words"][0] == {"word": "בראשית", "value": 913}
    assert d["total"] == sum(w["value"] for w in d["segments"][0]["words"])
    assert client.get("/api/tools/gematria", params={"ref": "Nope 9"}).status_code == 404
    c = client.get("/api/tools/gematria", params={"ref": "Genesis 1"}).json()
    assert len(c["segments"]) == 2
    s = client.get("/api/tools/same", params={"value": 913, "book": "Genesis"}).json()
    assert s["matches"][0]["word"] == "בראשית"
    assert client.get("/api/tools/same", params={"value": 1, "book": "Zzz"}).status_code == 404


def test_english_version_ignored(fnode, client):
    from bhm import library
    library.import_version(fnode.con, {
        "title": "Genesis", "heTitle": "בראשית", "versionTitle": "Eng", "language": "en",
        "license": "Public Domain", "categories": ["Tanakh", "Torah"], "sectionNames": ["Chapter", "Verse"],
        "text": [["In the beginning God created", "And the earth"]]}, "test", "h")
    d = client.get("/api/tools/gematria", params={"ref": "Genesis 1:1"}).json()
    assert d["segments"][0]["words"][0]["word"] == "בראשית"
    s = client.get("/api/tools/same", params={"value": 913, "book": "Genesis"}).json()
    assert s["matches"][0]["word"] == "בראשית" and s["truncated"] is False


def test_same_truncates(client, monkeypatch):
    monkeypatch.setattr(T, "MAX_SCAN_WORDS", 1)
    s = client.get("/api/tools/same", params={"value": 99999, "book": "Genesis"}).json()
    assert s["truncated"] is True
