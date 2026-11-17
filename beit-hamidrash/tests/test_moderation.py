import time


def _post(client, user, kind, target, body, ref=None):
    r = client.post("/api/events", json={"user": user, "kind": kind, "target": target, "body": body, "ref": ref})
    assert r.status_code == 200, r.text
    return r.json()


def _feed_ids(client):
    return [e["id"] for e in client.get("/api/feed").json()]


def test_queue_hide_unhide(client):
    art = _post(client, "reuven", "article", None, {"title": "כותרת", "text": "<b>טקסט</b>"})
    _post(client, "shimon", "report", art["id"], {"reason": "ספאם"})
    q = client.get("/api/moderation/queue?as=authority").json()
    assert q["is_moderator"] is True
    assert q["items"][0]["id"] == art["id"] and q["items"][0]["report_count"] == 1
    assert q["items"][0]["reports"][0]["reason"] == "ספאם"
    assert client.get("/api/moderation/queue?as=shimon").json()["is_moderator"] is False

    _post(client, "authority", "hide", art["id"], {"reason": "הופרו הכללים"})
    assert client.get("/api/moderation/queue").json()["items"] == []
    h = client.get("/api/moderation/hidden?as=authority").json()
    assert h["items"][0]["id"] == art["id"]
    assert h["items"][0]["hidden_by"]["reason"] == "הופרו הכללים"
    assert h["items"][0]["hidden_by"]["by_name"]
    assert art["id"] not in _feed_ids(client)

    time.sleep(1.1)  # ledger orders by second-resolution ts, then id
    _post(client, "authority", "unhide", art["id"], {"reason": "טעות"})
    assert client.get("/api/moderation/hidden").json()["items"] == []
    assert art["id"] in _feed_ids(client)
    assert len(client.get("/api/moderation/queue").json()["items"]) == 1


def test_non_moderator_hide_has_no_effect(client):
    art = _post(client, "reuven", "article", None, {"title": "t", "text": "x"})
    _post(client, "shimon", "report", art["id"], {"reason": "r"})
    _post(client, "shimon", "hide", art["id"], {"reason": "ניסיון"})
    assert client.get("/api/moderation/hidden").json()["items"] == []
    assert len(client.get("/api/moderation/queue").json()["items"]) == 1
    assert art["id"] in _feed_ids(client)


def test_unknown_user(client):
    assert client.get("/api/moderation/queue?as=nobody").status_code == 404


def test_no_text_unless_local_moderator(client):
    art = _post(client, "reuven", "article", None, {"title": "t", "text": "סודי"})
    _post(client, "shimon", "report", art["id"], {"reason": "ספאם"})
    for url in ("/api/moderation/queue", "/api/moderation/queue?as=shimon"):
        it = client.get(url).json()["items"][0]
        assert it == {"id": art["id"], "report_count": 1}
    _post(client, "authority", "hide", art["id"], {"reason": "x"})
    for url in ("/api/moderation/hidden", "/api/moderation/hidden?as=shimon"):
        assert client.get(url).json()["items"] == [{"id": art["id"]}]
    assert "text" in client.get("/api/moderation/hidden?as=authority").json()["items"][0]


def test_remote_moderator_gets_no_text(fnode):
    from fastapi.testclient import TestClient
    from bhm.api import create_app
    art = _post(TestClient(create_app(fnode)), "reuven", "article", None, {"title": "t", "text": "x"})
    _post(TestClient(create_app(fnode)), "shimon", "report", art["id"], {"reason": "r"})
    remote = TestClient(create_app(fnode), client=("8.8.8.8", 1))
    it = remote.get("/api/moderation/queue?as=authority").json()["items"][0]
    assert it == {"id": art["id"], "report_count": 1}
