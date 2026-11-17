def _post(client, body, user="reuven"):
    return client.post("/api/events", json={"user": user, "kind": "sheet", "body": body})


def test_preview(client):
    r = client.post("/api/sheets/preview", json={"items": [{"ref": "Genesis 1:1"}, {"ref": "Nope 9:9"}, {"text": "שלום"}]}).json()
    assert [i["ok"] for i in r["items"]] == [True, False, True] and r["ok"] is False
    assert "בְּרֵאשִׁית" in r["items"][0]["text"] and r["items"][0]["version"] == "Test PD"


def test_publish_list_get(client):
    e = _post(client, {"title": "דף א", "notes": "n", "items": [{"ref": "Genesis 1"}, {"text": "<b>x</b>"}, {"ref": "Zzz 1"}]}).json()
    lst = client.get("/api/sheets").json()
    assert len(lst) == 1 and lst[0]["id"] == e["id"] and lst[0]["items"] == 3 and lst[0]["refs"] == 2
    s = client.get(f"/api/sheets/{e['id']}").json()
    assert s["title"] == "דף א" and s["author_name"] == "ראובן"
    assert s["items"][0]["ok"] and len(s["items"][0]["segments"]) == 2 and s["items"][0]["license"] == "Public Domain"
    assert s["items"][1] == {"type": "text", "text": "<b>x</b>", "ok": True}
    assert s["items"][2]["ok"] is False


def test_missing_and_invalid(client):
    assert client.get("/api/sheets/nope").status_code == 404
    assert _post(client, {"title": "x", "items": []}).status_code == 400
