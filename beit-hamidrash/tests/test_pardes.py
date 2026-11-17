import pytest

from bhm import library
from bhm.features import pardes

BOOK = {"title": "Pardes Rimmonim", "heTitle": "פרדס רמונים", "versionTitle": "T PD", "language": "he",
        "license": "Public Domain", "categories": ["Kabbalah"], "sectionNames": ["Gate", "Chapter", "Paragraph"],
        "text": [[["השער הראשון", "ידוע ומפורסם"], ["פרק ב"]], [["שער ב"]]]}


def test_gates_meta(client):
    d = client.get("/api/pardes/gates").json()
    assert len(d["gates"]) == 32
    assert d["gates"][0]["title"] and d["gates"][0]["refs"] == []


def test_gates_refs(fnode, client):
    library.import_version(fnode.con, BOOK, "test", "h")
    g = client.get("/api/pardes/gates").json()["gates"]
    assert g[0]["refs"] == ["Pardes Rimmonim 1:1:1", "Pardes Rimmonim 1:2:1"]
    assert g[1]["refs"] == ["Pardes Rimmonim 2:1:1"]


def test_site_serves(client):
    r = client.get("/api/pardes/site/index.html")
    assert r.status_code == 200 and "html" in r.headers["content-type"]
    assert client.get("/api/pardes/site/").status_code == 200
    assert client.get("/api/pardes/site/data/meta.json").status_code == 200


@pytest.mark.parametrize("p", ["../README.md", "..%2fREADME.md", "%2e%2e/README.md", "data/../../README.md",
                               "../beit-hamidrash/bhm/api.py", "/etc/passwd", "..\\README.md",
                               "tools/build_data.py", "data", "assets", "nope.html", "%00.html"])
def test_traversal_and_bad(client, p):
    assert client.get("/api/pardes/site/" + p).status_code in (400, 404)


def test_safe_path_unit(tmp_path, monkeypatch):
    (tmp_path / "pardes").mkdir()
    (tmp_path / "pardes" / "a.html").write_text("x")
    (tmp_path / "secret.html").write_text("s")
    (tmp_path / "pardes" / "link.html").symlink_to(tmp_path / "secret.html")
    monkeypatch.setattr(pardes, "SITE", tmp_path / "pardes")
    assert pardes.safe_path("a.html")
    assert pardes.safe_path("../secret.html") is None
    assert pardes.safe_path("link.html") is None
    assert pardes.safe_path("..") is None
