import pytest
from fastapi.testclient import TestClient

from bhm import library
from bhm.api import create_app
from bhm.node import Node

SAMPLE = {"title": "Genesis", "heTitle": "בראשית", "versionTitle": "Test PD", "language": "he",
          "license": "Public Domain", "categories": ["Tanakh", "Torah"], "sectionNames": ["Chapter", "Verse"],
          "text": [["בְּרֵאשִׁית בָּרָא אֱלֹהִים", "וְהָאָרֶץ הָיְתָה תֹהוּ"], ["וַיְכֻלּוּ הַשָּׁמַיִם"]]}
SAMPLE_COMM = {"title": "Rashi on Genesis", "heTitle": "רש\"י על בראשית", "versionTitle": "Test PD", "language": "he",
               "license": "Public Domain", "categories": ["Tanakh", "Rishonim on Tanakh", "Rashi", "Torah"],
               "sectionNames": ["Chapter", "Verse", "Comment"], "text": [[["בראשית - אמר רבי יצחק"], ["תהו ובהו - תהו לשון תמה"]]]}


@pytest.fixture
def fnode(tmp_path):
    """A fresh node with an authority, two users and a tiny library (Genesis + Rashi)."""
    n = Node(tmp_path / "node")
    n.init_authority()
    n.create_user("reuven", "ראובן")
    n.create_user("shimon", "שמעון")
    library.import_version(n.con, SAMPLE, "test", "h")
    library.import_version(n.con, SAMPLE_COMM, "test", "h")
    return n


@pytest.fixture
def client(fnode):
    return TestClient(create_app(fnode))
