from bhm.features import sources_ai


def ask(client, q):
    return client.post("/api/sources_ai/ask", json={"question": q})


def test_no_model_no_network(client, monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    def boom(*a):
        raise AssertionError("network")
    monkeypatch.setattr(sources_ai, "_call_model", boom)
    d = ask(client, "מה פירוש תהו ובהו?").json()
    assert d["summary"] is None and not d["model_enabled"]
    assert any("Rashi" in s["ref"] for s in d["sources"])


def test_model_mocked_labeled(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://x")
    seen = {}

    def fake(url, model, prompt):
        seen.update(url=url, model=model, prompt=prompt)
        return "תהו לשון תמה [Rashi on Genesis 1:2]"
    monkeypatch.setattr(sources_ai, "_call_model", fake)
    d = ask(client, "תהו ובהו").json()
    assert d["summary"]["label"] == "סיכום ממוחשב, אינו פסק" and d["summary"]["ai_generated"]
    assert seen["model"] == "dictalm" and "תהו" in seen["prompt"]


def test_no_summary_without_sources(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://x")
    monkeypatch.setattr(sources_ai, "_call_model", lambda *a: "bla")
    d = ask(client, "זזזזזזז קקקקקק").json()
    assert d["sources"] == [] and d["summary"] is None


def test_model_failure_degrades(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://x")
    monkeypatch.setenv("OLLAMA_MODEL", "m2")

    def boom(*a):
        raise OSError("down")
    monkeypatch.setattr(sources_ai, "_call_model", boom)
    d = ask(client, "בראשית ברא").json()
    assert d["sources"] and d["summary"] is None and d["model_error"]


def test_validation_and_status(client):
    assert ask(client, "א").status_code == 400
    assert ask(client, "x" * 501).status_code == 400
    assert client.get("/api/sources_ai/status").json()["model_enabled"] is False


def test_fts_path(fnode, client):
    fnode.con.execute("CREATE VIRTUAL TABLE search_fts USING fts5(ref, text)")
    fnode.con.execute("INSERT INTO search_fts VALUES ('Fake 1:1','תהו ובהו בענין')")
    fnode.con.commit()
    d = ask(client, "תהו").json()
    assert d["sources"][0]["ref"] == "Fake 1:1"
