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


def test_vocalized_text_found_by_scan(fnode, client):
    vid = fnode.con.execute("SELECT version_id FROM segments LIMIT 1").fetchone()[0]
    fnode.con.execute("INSERT INTO segments(version_id, path, seq, ref, text) VALUES (?,?,?,?,?)",
                      (vid, "voc/1", 99999, "Voc 1:1", "וְהָאָ֖רֶץ הָיְתָ֥ה זְזִקְקֻ֖מם־לוג"))
    fnode.con.commit()
    d = ask(client, "זזקקמם").json()
    assert any(s["ref"] == "Voc 1:1" for s in d["sources"])
    assert d["partial"] is False


def test_rate_limit_and_log_cap(fnode, client, monkeypatch):
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    codes = [ask(client, "בראשית ברא").status_code for _ in range(12)]
    assert codes[:10] == [200] * 10 and codes[10] == 429
    n = fnode.con.execute("SELECT COUNT(*) FROM sources_ai_log").fetchone()[0]
    assert n <= sources_ai.LOG_KEEP


def test_model_busy_429(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://x")
    monkeypatch.setattr(sources_ai, "_call_model", lambda *a: "x")
    assert sources_ai._MODEL_SEM.acquire(blocking=False)
    try:
        assert ask(client, "בראשית ברא").status_code == 429
    finally:
        sources_ai._MODEL_SEM.release()
