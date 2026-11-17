from pathlib import Path

from bhm.features.compliance import md_to_html, ORDER


def test_list(client):
    d = client.get("/api/compliance").json()
    assert [i["slug"] for i in d["items"]] == ORDER
    assert "טיוטה לבדיקת עורך דין" in d["disclaimer"]


def test_all_docs_drafts_and_html(client):
    for s in ORDER:
        d = client.get(f"/api/compliance/{s}").json()
        assert "טיוטה לבדיקת עורך דין" in d["markdown"]
        assert d["html"].startswith("<h1>")


def test_404_and_traversal(client):
    assert client.get("/api/compliance/nope").status_code == 404
    assert client.get("/api/compliance/..%2Fprivacy").status_code in (404, 422)


def test_md_escapes():
    h = md_to_html("# <script>alert(1)</script>\n\n- <img src=x onerror=1>\n\n**b** & <b>")
    assert "<script" not in h and "<img" not in h and "<b>" not in h
    assert "<strong>b</strong>" in h and "&amp;" in h and "<li>" in h


def test_no_external_urls_in_js():
    js = (Path(__file__).parent.parent / "web/features/compliance.js").read_text(encoding="utf-8")
    assert "http://" not in js and "https://" not in js
