import time

from bhm import ledger


def pk(fnode, u):
    return fnode.identity(u).pubkey


def test_list_and_profile(fnode, client):
    fnode.post("reuven", "article", {"title": "t", "text": "x"})
    fnode.post("reuven", "commentary", {"text": "c"}, ref="Genesis 1:1")
    by = {p["name"]: p for p in client.get("/api/profiles").json()}
    assert by["ראובן"]["posts"] == 2 and "שמעון" in by
    p = client.get(f"/api/profiles/{pk(fnode, 'reuven')}").json()
    assert p["posts_by_kind"] == {"article": 1, "commentary": 1}
    assert p["fingerprint"] and p["followers_count"] == 0
    assert client.get("/api/profiles/nope").status_code == 404


def test_follow_latest_wins_and_feed(fnode, client):
    s, r = pk(fnode, "shimon"), pk(fnode, "reuven")
    art = fnode.post("reuven", "article", {"title": "t", "text": "x"})
    fnode.post("shimon", "follow", {"subject": r})
    assert client.get(f"/api/profiles/{r}").json()["followers_count"] == 1
    assert [e["id"] for e in client.get(f"/api/profiles/{s}/feed").json()] == [art["id"]]
    time.sleep(1.1)
    fnode.post("shimon", "unfollow", {"subject": r})
    assert client.get(f"/api/profiles/{r}").json()["followers_count"] == 0
    assert client.get(f"/api/profiles/{s}/feed").json() == []


def test_endorsements_and_hidden(fnode, client):
    r = pk(fnode, "reuven")
    art = fnode.post("reuven", "article", {"title": "t", "text": "x"})
    fnode.post("shimon", "endorse", {}, target=art["id"])
    fnode.post("shimon", "follow", {"subject": r})
    assert client.get(f"/api/profiles/{r}").json()["endorsements_received"] == 1
    fnode.post("authority", "hide", {}, target=art["id"])
    p = client.get(f"/api/profiles/{r}").json()
    assert p["posts"] == 0 and p["endorsements_received"] == 0
    assert client.get(f"/api/profiles/{pk(fnode, 'shimon')}/feed").json() == []
    assert ledger.hidden(fnode.con) == {art["id"]}


def test_hidden_follow_ignored(fnode, client):
    r = pk(fnode, "reuven")
    f = fnode.post("shimon", "follow", {"subject": r})
    fnode.post("authority", "hide", {}, target=f["id"])
    assert client.get(f"/api/profiles/{r}").json()["followers_count"] == 0


def test_static_and_nav(client):
    assert client.get("/static/features/profiles.js").status_code == 200
    assert any(f["name"] == "profiles" for f in client.get("/api/features").json())


def test_malformed_follow_subject_ignored(fnode, client):
    from bhm import ledger as L
    r = pk(fnode, "reuven")
    for subj in (["x"], "y" * 200, 5):
        L.insert(fnode.con, L.make_event(fnode.identity("shimon"), "follow", {"subject": subj}))
    assert client.get("/api/profiles").status_code == 200
    assert client.get(f"/api/profiles/{r}").status_code == 200
    assert client.get(f"/api/profiles/{pk(fnode, 'shimon')}/feed").json() == []


def test_feed_only_known_authors_and_cap(fnode, client):
    s, r = pk(fnode, "shimon"), pk(fnode, "reuven")
    art = fnode.post("reuven", "article", {"title": "t", "text": "x"})
    from bhm import ledger as L
    for i in range(600):
        L.insert(fnode.con, L.make_event(fnode.identity("shimon"), "follow", {"subject": f"ghost{i}"}))
    fnode.post("shimon", "follow", {"subject": r})
    assert [e["id"] for e in client.get(f"/api/profiles/{s}/feed").json()] == [art["id"]]
