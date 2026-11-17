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


def test_sw_network_first_and_never_cache(client):
    t = client.get("/api/pwa/sw.js").text
    assert "cacheFirst" not in t
    for p in ("/api/moderation/", "/api/admin/", "/api/sources_ai/"):
        assert p in t


def test_cache_version_from_mtimes(tmp_path):
    from bhm.features import pwa
    (tmp_path / "a.js").write_text("x")
    v1 = pwa.compute_cache_version(tmp_path)
    import os
    os.utime(tmp_path / "a.js", ns=(1, 2_000_000_000))
    assert pwa.compute_cache_version(tmp_path) != v1
    assert pwa.CACHE_VERSION in pwa.SW_JS
