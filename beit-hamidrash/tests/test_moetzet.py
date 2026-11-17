def test_index_and_topic(client):
    d = client.get("/api/moetzet").json()
    assert len(d["topics"]) == 10 and "אינו פסק הלכה" in d["notice"]
    t = client.get("/api/moetzet/stam").json()
    assert t["positions"] and all("verdict" in p for p in t["positions"])
    assert client.get("/api/moetzet/nope").status_code == 404


def test_verified_quotes_have_refs(client):
    for k in [t["key"] for t in client.get("/api/moetzet").json()["topics"]]:
        for p in client.get(f"/api/moetzet/{k}").json()["positions"]:
            if p["verdict"] == "verified" and p["kind"] == "classical_local":
                assert p.get("ref")
