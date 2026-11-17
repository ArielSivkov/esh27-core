from bhm.features.articles import gematria


def _post(client, user, kind, body, **kw):
    r = client.post("/api/events", json={"user": user, "kind": kind, "body": body, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def _art(client, text="ראו Genesis 1:1 ושם.", title="כותרת", user="reuven"):
    return _post(client, user, "article", {"title": title, "text": text})


def test_gematria():
    assert gematria("א") == 1 and gematria("טו") == 15 and gematria("קכ") == 120
    assert gematria("abc") is None and gematria("") is None


def test_list_newest_first_and_hidden(client, fnode):
    a1 = _art(client, title="ראשון")
    a2 = _art(client, title="שני")
    # ensure ordering by ts regardless of same-second timestamps
    fnode.con.execute("UPDATE events SET ts='2030-01-01T00:00:00+00:00' WHERE id=?", (a2["id"],))
    fnode.con.commit()
    lst = client.get("/api/articles").json()
    assert [x["title"] for x in lst] == ["שני", "ראשון"]
    assert lst[0]["author_name"] == "ראובן"
    # the authority (a moderator) hides a2
    fnode.post("authority", "hide", {}, target=a2["id"])
    lst = client.get("/api/articles").json()
    assert [x["id"] for x in lst] == [a1["id"]]
    assert client.get(f"/api/articles/{a2['id']}").status_code == 404


def test_get_404(client):
    assert client.get("/api/articles/nope").status_code == 404


def test_edit_by_author_replaces_others_ignored(client):
    a = _art(client, text="טקסט ראשון", title="כותרת א")
    _post(client, "shimon", "edit", {"text": "חבלה", "title": "פרוץ"}, target=a["id"])
    d = client.get(f"/api/articles/{a['id']}").json()
    assert d["text"] == "טקסט ראשון" and d["title"] == "כותרת א"
    assert d["ignored_edits"] == 1 and len(d["history"]) == 1
    _post(client, "reuven", "edit", {"text": "טקסט מתוקן", "title": "כותרת ב"}, target=a["id"])
    d = client.get(f"/api/articles/{a['id']}").json()
    assert d["text"] == "טקסט מתוקן" and d["title"] == "כותרת ב"
    assert [h["kind"] for h in d["history"]] == ["article", "edit"]
    assert client.get("/api/articles").json()[0]["edited"] is True


def test_refs_english(client):
    a = _art(client, text="See Genesis 1:1 and also Genesis 2:1 plus Genesis 9:9 and Nowhere 3:3.")
    d = client.get(f"/api/articles/{a['id']}").json()
    refs = {r["ref"]: r for r in d["refs"]}
    assert set(refs) == {"Genesis 1:1", "Genesis 2:1"}
    assert "אֱלֹהִים" in refs["Genesis 1:1"]["snippet"]
    t = d["text"]
    r = refs["Genesis 1:1"]
    assert t[r["start"]:r["end"]] == "Genesis 1:1"


def test_refs_hebrew_and_chapter(client):
    a = _art(client, text="בראשית א:א וגם בראשית א:ב ובבראשית ב. ועוד בראשית ב:א; ושמות ג:ג.")
    d = client.get(f"/api/articles/{a['id']}").json()
    refs = [r["ref"] for r in d["refs"]]
    assert refs == ["Genesis 1:1", "Genesis 1:2", "Genesis 2:1"]
    assert d["refs"][0]["match"] == "בראשית א:א"


def test_refs_hebrew_daf(client, fnode):
    cur = fnode.con.execute(
        "INSERT INTO versions(title,he_title,version_title,language,license,tier,categories,origin,sha256,imported_at) "
        "VALUES ('Berakhot','ברכות','T','he','Public Domain','certain','[]','t','h','now')")
    fnode.con.execute("INSERT INTO segments(version_id,ref,path,seq,text) VALUES (?,?,?,?,?)",
                      (cur.lastrowid, "Berakhot 2a:1", "2a.1", 0, "מאימתי קורין"))
    fnode.con.commit()
    a = _art(client, text='ברכות ב ע"א ו-Berakhot 2a')
    refs = client.get(f"/api/articles/{a['id']}").json()["refs"]
    assert [r["ref"] for r in refs] == ["Berakhot 2a", "Berakhot 2a"]
    assert refs[0]["segment_ref"] == "Berakhot 2a:1" and refs[0]["snippet"] == "מאימתי קורין"


def test_html_is_not_interpreted_server_side(client):
    a = _art(client, text="<script>alert(1)</script> Genesis 1:1", title="<b>x</b>")
    d = client.get(f"/api/articles/{a['id']}").json()
    assert d["title"] == "<b>x</b>"  # raw data; the UI escapes with BHM.esc
    assert [r["ref"] for r in d["refs"]] == ["Genesis 1:1"]


def test_js_served_and_escapes(client):
    js = client.get("/static/features/articles.js").text
    assert "BHM.esc" in js and "register('articles'" in js and "register('article'" in js
    assert any(f["name"] == "articles" for f in client.get("/api/features").json())


def test_edit_chain_and_deterministic_order(client, fnode):
    a = _art(client, text="orig", title="T")
    e1 = _post(client, "reuven", "edit", {"text": "v1"}, target=a["id"])
    e2 = _post(client, "reuven", "edit", {"text": "v2", "prev": e1["id"]}, target=a["id"])
    e3 = _post(client, "reuven", "edit", {"text": "fork", "prev": a["id"]}, target=a["id"])
    # make the fork the newest by ts; the longer chain must still win
    fnode.con.execute("UPDATE events SET ts='2031-01-01T00:00:00+00:00' WHERE id=?", (e3["id"],))
    fnode.con.commit()
    assert client.get(f"/api/articles/{a['id']}").json()["text"] == "v2"


def test_edit_same_ts_uses_received_order(client, fnode):
    a = _art(client, text="orig")
    ids = [_post(client, "reuven", "edit", {"text": t}, target=a["id"])["id"] for t in ("a", "b", "c")]
    fnode.con.execute("UPDATE events SET ts='2031-01-01T00:00:00+00:00' WHERE kind='edit'")
    fnode.con.commit()
    assert client.get(f"/api/articles/{a['id']}").json()["text"] == "c"
