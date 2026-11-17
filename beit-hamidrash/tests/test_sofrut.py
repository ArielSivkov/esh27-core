"""Tests for the sofrut feature. All data comes from small fixtures; nothing depends on the real library."""
import shutil
import sqlite3
import subprocess

import pytest

from bhm import library
from bhm.features import sofrut

RAMBAM_T = sofrut.RAMBAM
MAS, LEN = sofrut.MASORAH, sofrut.LENINGRAD


def put(node, title, version_title, text, he=None):
    ok, dec, n = library.import_version(node.con, {"title": title, "heTitle": he or title, "versionTitle": version_title, "language": "he",
                                                   "license": "Public Domain", "categories": ["Test"], "sectionNames": [], "text": text},
                                        "test", "h")
    assert ok, dec.reason
    return n


GEN_MAS = [["בְּרֵאשִׁית בָּרָא", "וְהָאָרֶץ הָיְתָה {פ}", "וַיֹּאמֶר אֱלֹהִים {ס}", "וַיַּרְא אֱלֹהִים {פ}"], ["וַיְכֻלּוּ הַשָּׁמַיִם {פ}"]]
GEN_LEN = [["בְּרֵאשִׁית בָּרָא", "וְהָאָרֶץ הָיְתָה (פ)", "וַיֹּאמֶר אֱלֹהִים (פ)", "וַיַּרְא אֱלֹהִים"], ["וַיְכֻלּוּ הַשָּׁמַיִם (ס)"]]

# a miniature of Rambam's list (same wording and structure as Tefillin, Mezuzah and Torah Scroll 8:4)
LIST_FIXTURE = (
    "הקדמה על הספרים. ספר בראשית:יהי רקיע ויכלו שתיהן פתוחות אל האשה אמר סתומה מנין הפתוחות שתים והסתומות אחת הכל שלש:"
    "ספר ואלה שמות:ויקם מלך חדש וילך איש שתיהן פתוחות ומשה היה רעה סתומה מנין הפתוחות שתים ומנין הסתומות אחת הכל שלש פרשיות:"
    "ספר ויקרא:ואם מן הצאן ואם מן העוף כולן פתוחות והן שתים (ויקרא כו) ואם בזאת סתומה מנין הפתוחות שתים והסתומות אחת הכל שלש:"
    "ספר במדבר סיני:בני ראובן פתוחה לבני שמעון כולן פתוחות ואלה פקודי סתומה מנין הפתוחות שתים והסתומות אחת הכל שלש:"
    "ספר אלה הדברים:ויאמר יי' אלי שלשתן סתומות והיה כי יביאך פתוחה והיה עקב כולן פתוחות והן שש עשר תעשר פתוחה "
    "מנין הפתוחות של ספר זה שתים והסתומות שלש הכל חמש מנין הפתוחות של כל התורה עשר ומנין הסתומות שבע הכל שבע עשרה:"
    "צורת שירת האזינו כל שיטה ושיטה יש באמצע ריוח אחד כצורת הפרשה הסתומה ונמצא כל שיטה חלוקה לשתים וכותבין אותה בשבעים שיטות "
    "ואלו הן התיבות שבראש כל שיטה ושיטה:האזינו יערף כל אלו התיבות שבראש ואלו הן התיבות שבראש כל חצי שיטה אחרונה שהן באמצע הדף:ותשמע תזל:"
    "שירת הים כותבין אותה בשלשים שיטות שיטה ראשונה כדרכה ושאר השיטות אחת מניחין באמצעה ריוח אחד:וזו היא צורתה")
# the fixture deliberately has the totals of the real list only for the five-book sum check (see test_rambam_parse)

DEUT32 = ["הַאֲזִינוּ הַשָּׁמַיִם וַאֲדַבֵּרָה וְתִשְׁמַע הָאָרֶץ אִמְרֵי־פִי", "יַעֲרֹף כַּמָּטָר לִקְחִי תִּזַּל כַּטַּל אִמְרָתִי"]
EX15 = ["אָז יָשִׁיר־מֹשֶׁה וּבְנֵי יִשְׂרָאֵל אֶת־הַשִּׁירָה הַזֹּאת לַיהוָה וַיֹּאמְרוּ לֵאמֹר", "אָשִׁירָה לַיהוָה כִּי־גָאֹה גָּאָה סוּס",
        "וְרֹכְבוֹ רָמָה בַיָּם עָזִּי"]
LIST_20 = "ואלו הן:" + "".join(f"({l}) פוסל מספר {i + 1}" for i, l in enumerate("אבגדהוזחטי")) + "(יא) שכתב האזכרות(יב) שחסר אפילו אות אחת" \
          "(יג) שהוסיף(יד) ד(טו) ה(טז) ו(יז) ז(יח) ח(יט) ט(כ) שתפר בלא גידי טהורה ושאר הדברים למצוה לא לעכב."


def rambam_text():
    ch8 = ["א", "ב", "ג", LIST_FIXTURE]
    return [[] for _ in range(7)] + [ch8, [], [LIST_20]]


@pytest.fixture
def snode(fnode):
    put(fnode, "Genesis", MAS, GEN_MAS)
    put(fnode, "Genesis", LEN, GEN_LEN)
    return fnode


@pytest.fixture
def full(snode):
    put(snode, RAMBAM_T, "Wikisource Mishneh Torah", rambam_text())
    put(snode, "Deuteronomy", MAS, [[] for _ in range(31)] + [DEUT32])
    put(snode, "Exodus", MAS, [[] for _ in range(14)] + [EX15])
    put(snode, "Tractate Soferim", "Talmud Bavli, Vilna 1883 ed.", [[] for _ in range(11)] + [["ה"] * 10 + ["שירת הים שלשים שיטין. אז. לאמר. ורכבו."]])
    return snode


# ------------------------------------------------------------------------------------------------ pure functions
@pytest.mark.parametrize("s,n", [("שלש וארבעים", 43), ("מאה וששים וארבע", 164), ("שש מאות וששים ותשע", 669), ("מאתים ותשעים", 290),
                                 ("שלש מאות ושבעים ותשע", 379), ("תשע וששים", 69), ("אחת עשרה", 11), ("שתים עשרה", 12), ("שש", 6),
                                 ("מאה וחמשים ושמונה", 158)])
def test_heb_number(s, n):
    assert sofrut.heb_number(s) == n


def test_heb_number_rejects_non_numbers():
    assert sofrut.heb_number("עשר תעשר") is None and sofrut.heb_number("") is None and sofrut.heb_number("ויאמר") is None


def test_find_breaks():
    assert sofrut.find_breaks("וַיְהִי עֶרֶב׃ {פ}") == [("open", "end")]
    assert sofrut.find_breaks("בראשית (ס)") == [("closed", "end")]
    assert sofrut.find_breaks("לֹא תִּרְצָח {ס} לֹא תִּנְאָף {ס} לֹא תִגְנֹב׃ {פ}") == [("closed", "mid"), ("closed", "mid"), ("open", "end")]
    assert sofrut.find_breaks("אֶרֶץ (ספק פרשה סתומה בכתר) [קרי]") == []      # notes are not breaks
    assert sofrut.find_breaks("אות (ס) (ספק פרשה סתומה בכתר ארם צובה)") == [("closed", "end")]
    assert sofrut.find_breaks("יְהוָה&thinsp;׀&thinsp;יִמְלֹךְ") == []


def test_words_of():
    assert sofrut.words_of("אָז יָשִׁיר־מֹשֶׁה {פ} (כתיב) [קרי]&thinsp;׀&thinsp;וַיֹּאמְרוּ") == ["אז", "ישיר", "משה", "ויאמרו"]


def test_parse_groups_counts():
    g = sofrut._parse_groups("ויאמר יי' אל משה בא פתוחה אחת עשרה פרשיות אלו כולן סתומות ויהי כולן פתוחות והן שבע פרשיות אל האשה שתיהן סתומות "
                             "כי יסיתך כולן סתומות והן שש עשר תעשר פתוחה")
    assert [(x["kind"], x["count"]) for x in g] == [("open", 1), ("closed", 11), ("open", 7), ("closed", 2), ("closed", 6), ("open", 1)]
    assert g[-1]["incipits"] == "עשר תעשר"            # 'עשר' there is an incipit, not part of the number 16
    assert g[0]["incipits"] == "ויאמר יי' אל משה בא"


def test_rambam_parse_fixture():
    r = sofrut.parse_rambam_sections(sofrut.clean_text(LIST_FIXTURE))
    assert r["found"] and [b["title"] for b in r["books"]] == sofrut.BOOKS
    assert r["books"][0]["stated"] == {"open": 2, "closed": 1, "total": 3, "consistent": True}
    assert r["books"][1]["stated"]["total"] == 3                      # '... הכל שלש פרשיות'
    assert r["books"][4]["stated"] == {"open": 2, "closed": 3, "total": 5, "consistent": True}
    assert r["stated_total"] == {"open": 10, "closed": 7, "total": 17, "consistent": True}
    assert r["sum_of_books"] == {"open": 10, "closed": 7, "total": 17} and r["sum_matches_stated_total"]
    assert r["books"][4]["parsed"]["counted_open"] == 1 + 6 + 1 and r["books"][4]["parsed"]["counted_closed"] == 3


def test_rambam_parse_absent():
    r = sofrut.parse_rambam_sections("הלכות ספר תורה בלי רשימת פרשיות")
    assert r["found"] is False and r["reason"] and r["books"] == []


def test_parse_rambam20():
    items = sofrut.parse_rambam20(LIST_20)
    assert [i["n"] for i in items] == list(range(1, 21))
    assert items[11]["text"] == "שחסר אפילו אות אחת" and items[11]["digital"]["level"] == "yes"
    assert items[19]["text"] == "שתפר בלא גידי טהורה" and items[19]["tail"].startswith("ושאר הדברים")
    assert items[0]["digital"]["level"] == "no"


def test_align_openers_and_split():
    words = "א ב ג ד ה ו ז ח ט י".split()
    al = sofrut.align_openers(words, [["א"], ["ד"], ["ח"]])
    assert al["starts"] == [0, 3, 7] and al["mismatches"] == []
    al = sofrut.align_openers(words, [["א"], ["ד"], ["צ"]])        # unmatched opener is reported, not hidden
    assert al["mismatches"] == [2]
    assert sofrut.align_openers(words, []) is None
    assert sofrut.split_by_weight(["אא", "בב", "גג", "דד"], [1, 1]) == [["אא", "בב"], ["גג", "דד"]]
    assert all(sofrut.split_by_weight(list("אבגדה"), [27, 34, 27])) and len(sofrut.split_by_weight(list("אבגדה"), [27, 34, 27])) == 3
    assert sofrut.split_by_weight(["אב"], [1, 1]) == [["אב"]]


def test_norm_opener():
    assert sofrut.norm_opener("הליי'") == "הליהוה" and sofrut.norm_opener("ה׳") == "יהוה" and sofrut.norm_opener("ויי'") == "ויהוה"


# ------------------------------------------------------------------------------------------------ static data
def test_laws_static():
    ids = [x["id"] for x in sofrut.LAWS]
    assert len(ids) == len(set(ids)) >= 15
    for law in sofrut.LAWS:
        assert 1 <= len(law["refs"]) <= 3, law["id"]
        assert law["digital"]["level"] in ("yes", "partial", "no") and law["digital"]["text"] and law["views"]
        assert all(v["who"] and v["gist"] for v in law["views"])
        for ref in law["refs"] + [v["ref"] for v in law["views"] if v["ref"]]:
            assert any(ref.startswith(p) for p in (sofrut.RAMBAM, sofrut.SA, sofrut.TUR, sofrut.TAZ, sofrut.SHACH, sofrut.GRA, sofrut.KS, sofrut.SOF)), ref
    assert {"yes", "partial", "no"} <= {x["digital"]["level"] for x in sofrut.LAWS}
    # every source family required by the task is used
    refs = " ".join(r for x in sofrut.LAWS for r in x["refs"])
    assert sofrut.RAMBAM in refs and sofrut.SA in refs and sofrut.KS in refs
    assert "ספר תורה" in sofrut.DISCLAIMER and "מגיה" in sofrut.DISCLAIMER


# ------------------------------------------------------------------------------------------------ API
def test_overview_without_data(client):
    r = client.get("/api/sofrut").json()
    assert r["editions"] == {"masorah": 0, "leningrad": 0} and r["rambam_sections_present"] is False and r["disclaimer"]
    assert {"label": "הלכות סת״ם", "href": "#/sofrut"} == sofrut.NAV
    p = client.get("/api/sofrut/parashiyot").json()
    assert p["available"] is False and p["rambam_found"] is False
    assert client.get("/api/sofrut/shirot").json()["available"] is False


def test_parashiyot_totals_and_diff(client, snode):
    p = client.get("/api/sofrut/parashiyot").json()
    assert p["available"] and p["rambam_found"] is False
    assert p["traditional"]["open"] == 290 and p["traditional"]["closed"] == 379 and p["traditional"]["total"] == 669
    by = {v["key"]: v for v in p["versions"]}
    m, l = by["masorah"], by["leningrad"]
    assert (m["totals"]["open"], m["totals"]["closed"], m["totals"]["total"]) == (3, 1, 4)
    assert (l["totals"]["open"], l["totals"]["closed"], l["totals"]["total"]) == (2, 1, 3)
    assert m["complete"] is False and m["totals"]["delta_total"] == 4 - 669
    g = m["books"][0]
    assert g["title"] == "Genesis" and g["verses"] == 5 and (g["open"], g["closed"]) == (3, 1)
    rows = {(x["ref"], x["slot"]): x for x in p["diff"]["rows"]}
    assert set(rows) == {("Genesis 1:3", "end"), ("Genesis 1:4", "end"), ("Genesis 2:1", "end")}
    assert rows[("Genesis 1:3", "end")]["type"] == "kind_differs" and rows[("Genesis 1:3", "end")]["masorah"] == "closed"
    assert rows[("Genesis 1:4", "end")]["type"] == "only_masorah" and rows[("Genesis 1:4", "end")]["leningrad"] is None
    assert p["diff"]["count"] == 3 and p["diff"]["by_type"] == {"kind_differs": 2, "only_masorah": 1, "only_leningrad": 0}
    assert p["diff"]["by_book"]["Genesis"] == 3 and p["diff"]["by_book"]["Exodus"] == 0


def test_breaks_endpoint(client, snode):
    r = client.get("/api/sofrut/parashiyot/breaks", params={"version": "leningrad", "book": "Genesis"}).json()
    assert r["open"] == 2 and r["closed"] == 1 and [b["ref"] for b in r["breaks"]] == ["Genesis 1:2", "Genesis 1:3", "Genesis 2:1"]
    assert client.get("/api/sofrut/parashiyot/breaks", params={"version": "x", "book": "Genesis"}).status_code == 400
    assert client.get("/api/sofrut/parashiyot/breaks", params={"version": "masorah", "book": "Exodus"}).status_code == 404


def test_mid_verse_breaks_are_counted_separately(fnode, client):
    put(fnode, "Exodus", MAS, [[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], ["אנכי {ס}", "לא תרצח {ס} לא תנאף {ס} לא תגנב {פ}"]])
    r = client.get("/api/sofrut/parashiyot/breaks", params={"version": "masorah", "book": "Exodus"}).json()
    assert [(b["ref"], b["kind"], b["slot"]) for b in r["breaks"]] == [
        ("Exodus 20:1", "closed", "end"), ("Exodus 20:2", "closed", "mid0"), ("Exodus 20:2", "closed", "mid1"), ("Exodus 20:2", "open", "end")]
    assert r["mid_verse"] == 2 and r["total"] == 4


def test_rambam_absent_is_reported_not_invented(client, snode):
    r = client.get("/api/sofrut/rambam-sections").json()
    assert r["found"] is False and r["books"] == [] and r["reason"] and "stated_total" not in r
    p = client.get("/api/sofrut/parashiyot").json()
    assert p["rambam_found"] is False and p["traditional"]["source"] == "מנין מקובל"


def test_rambam_present_changes_traditional_and_invalidates_cache(client, snode):
    assert client.get("/api/sofrut/parashiyot").json()["traditional"]["total"] == 669
    assert client.get("/api/sofrut/parashiyot").json()["cached"] is True
    put(snode, RAMBAM_T, "Wikisource Mishneh Torah", rambam_text())
    p = client.get("/api/sofrut/parashiyot").json()
    assert p["cached"] is False and p["rambam_found"] is True
    assert p["traditional"]["total"] == 17 and p["traditional"]["source"] == sofrut.SECTIONS_REF      # read from the library text
    g = [v for v in p["versions"] if v["key"] == "masorah"][0]["books"][0]
    assert g["rambam"] == {"open": 2, "closed": 1, "total": 3, "consistent": True} and g["delta_open"] == 1
    r = client.get("/api/sofrut/rambam-sections").json()
    assert r["found"] and r["ref"] == sofrut.SECTIONS_REF and r["sum_matches_stated_total"] and r["books"][2]["groups"][0]["incipits"].startswith("ואם מן הצאן")


def test_cache_behaviour(client, snode):
    assert client.get("/api/sofrut/parashiyot").json()["cached"] is False
    assert client.get("/api/sofrut/parashiyot").json()["cached"] is True
    assert client.get("/api/sofrut/parashiyot?refresh=true").json()["cached"] is False
    n = snode.con.execute("SELECT COUNT(*) FROM sofrut_cache WHERE name='parashiyot'").fetchone()[0]
    assert n == 1
    put(snode, "Genesis", MAS, GEN_LEN)               # re-import: different version ids -> recompute
    assert client.get("/api/sofrut/parashiyot").json()["cached"] is False


def test_read_only_connection_never_writes(snode):
    path = snode.home / "library.db"
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    r = sofrut.cached(con, "parashiyot", sofrut.BOOKS + [RAMBAM_T], lambda: sofrut.compute_parashiyot(con))
    assert r["cached"] is False and r["versions"][0]["totals"]["total"] == 4
    assert sofrut.laws_payload(con)["laws"]
    con.close()


def test_laws_endpoint_checks_refs(client, full):
    r = client.get("/api/sofrut/laws").json()
    assert r["disclaimer"] and len(r["laws"]) == len(sofrut.LAWS)
    assert r["all_refs_exist"] is False and f"{sofrut.SA} 275:2" in r["missing_refs"]
    law = [x for x in r["laws"] if x["id"] == "pasul20"][0]
    src = {s["ref"]: s for s in law["sources"]}
    assert src[f"{RAMBAM_T} 10:1"]["exists"] is True and "פוסל מספר" in src[f"{RAMBAM_T} 10:1"]["excerpt"]
    assert src[f"{RAMBAM_T} 7:9"]["exists"] is False
    assert len(r["rambam_20"]) == 20 and r["rambam_20"][11]["digital"]["level"] == "yes"
    assert r["digital_levels"]["no"]


def test_shirot_layout(client, full):
    r = client.get("/api/sofrut/shirot").json()
    assert r["available"] and r["illustration"] == "המחשה, לא תיקון סופרים" and r["frame"]["yam"]["above"][0] == "הבאים"
    hz = r["haazinu"]
    assert hz["line_count"] == 2 and hz["stated_lines"] == 2 and hz["form"] == "אריח על גבי אריח"
    l1, l2 = hz["lines"]
    assert [" ".join(s["words"]) for s in l1["segments"]] == ["האזינו השמים ואדברה", "ותשמע הארץ אמרי פי"]
    assert [" ".join(s["words"]) for s in l2["segments"]] == ["יערף כמטר לקחי", "תזל כטל אמרתי"]
    assert l1["segments"][0]["marks"] == [{"i": 0, "ref": "Deuteronomy 32:1"}] and l2["segments"][0]["marks"][0]["ref"] == "Deuteronomy 32:2"
    assert l1["opener_match"] and hz["alignment"]["mismatched_openers"] == []
    yam = r["yam"]
    assert yam["line_count"] == 3 and yam["stated_lines"] == 30            # fixture list is short: reported, not hidden
    assert [ln["gaps"] for ln in yam["lines"]] == [0, 1, 2]                # line 1 whole, then 1 gap, then 2 gaps
    assert " ".join(yam["lines"][0]["segments"][0]["words"]).startswith("אז ישיר משה")
    assert sum(len(s["words"]) for ln in yam["lines"] for s in ln["segments"]) == yam["words"]
    assert client.get("/api/sofrut/shirot").json()["cached"] is True


def test_shirot_missing_pieces(client, snode):
    r = client.get("/api/sofrut/shirot").json()
    assert r["available"] is False and r["yam"] is None and r["haazinu"] is None


def test_routes_prefix(client, fnode):
    paths = {r.path for r in sofrut.make_router(fnode).routes}
    assert len(paths) == 6 and all(p.startswith("/api/sofrut") for p in paths)
    feats = {f["name"]: f for f in client.get("/api/features").json()}
    assert feats["sofrut"]["js"] == "/static/features/sofrut.js" and feats["sofrut"]["nav"]["label"] == "הלכות סת״ם"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_syntax():
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "web" / "features" / "sofrut.js"
    assert subprocess.run(["node", "--check", str(p)], capture_output=True).returncode == 0
    src = p.read_text(encoding="utf-8")
    assert "BHM.register('sofrut'" in src and "esc(" in src and "innerHTML" in src
