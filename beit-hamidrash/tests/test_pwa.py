def test_sw(client):
    r = client.get("/api/pwa/sw.js")
    assert r.status_code == 200
    assert r.headers["service-worker-allowed"] == "/"
    assert "javascript" in r.headers["content-type"]
    assert "'/static/'" in r.text and "req.method !== 'GET'" in r.text


def test_manifest(client):
    r = client.get("/api/pwa/manifest.json")
    assert r.status_code == 200
    assert "manifest+json" in r.headers["content-type"]
    m = r.json()
    assert m["dir"] == "rtl" and m["lang"] == "he" and m["start_url"] == "/"
    assert m["icons"] and m["theme_color"]


def test_icon_and_offline(client):
    r = client.get("/api/pwa/icon.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml")
    r = client.get("/api/pwa/offline")
    assert r.status_code == 200 and 'dir="rtl"' in r.text


def test_js_served(client):
    r = client.get("/static/features/pwa.js")
    assert r.status_code == 200 and "serviceWorker" in r.text
