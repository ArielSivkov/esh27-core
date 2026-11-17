from datetime import date, timedelta

import pytest

from bhm.features import calendar as cal


def test_hebrew_date_known():
    h = cal.hebrew_date(date(2026, 11, 14))
    assert (h["year"], h["month"], h["day"]) == (5787, 9, 4)
    assert h["text"] == "ד׳ כסלו התשפ״ז"
    assert cal.fixed_to_hebrew(date(2023, 9, 16).toordinal()) == (5784, 7, 1)  # Rosh Hashana 5784
    assert cal.gematria(15) == "ט״ו" and cal.gematria(16) == "ט״ז" and cal.year_he(5784) == "התשפ״ד"


def test_parasha_known_dates():
    p = cal.parasha_for(date(2026, 11, 14), True)
    assert p["he"] == "תולדות" and p["en"] == "Toldot" and p["range"] == "Genesis 25:19-28:9"
    assert p["goto"] == "Genesis 25:19"
    assert cal.parasha_for(date(2026, 11, 10), True)["shabbat"] == "2026-11-14"  # weekday -> coming Shabbat
    assert cal.parasha_for(date(2021, 3, 13), False)["en"] == "Vayakhel, Pekudei"  # double parasha
    assert cal.parasha_for(date(2020, 4, 11), False)["holiday"] == "פסח"  # yom tov Shabbat


def test_israel_vs_diaspora_differ():
    d = date(2026, 5, 23)  # Shavuot 2nd day fell on Shabbat: diaspora only
    assert cal.parasha_for(d, False)["holiday"] == "שבועות"
    assert cal.parasha_for(d, True)["en"] == "Nasso"


def test_against_pyluach():
    pytest.importorskip("pyluach")
    from pyluach import dates, parshios
    d = date(2000, 1, 1)
    while d < date(2060, 1, 1):
        h = dates.GregorianDate(d.year, d.month, d.day).to_heb()
        assert cal.fixed_to_hebrew(d.toordinal()) == (h.year, h.month, h.day)
        if d.weekday() == 5:
            for israel in (True, False):
                assert (parshios.getparsha(h, israel=israel) or []) == cal.parasha_for(d, israel)["indexes"]
        d += timedelta(days=1)


def test_daily_plan():
    assert cal.TOTAL_CHAPTERS == 929
    assert cal.daily_chapter(cal.PLAN_START)["ref"] == "Genesis 1"
    assert cal.daily_chapter(cal.PLAN_START + timedelta(days=50))["ref"] == "Exodus 1"
    assert cal.daily_chapter(cal.PLAN_START + timedelta(days=928))["ref"] == "II Chronicles 36"
    assert cal.daily_chapter(cal.PLAN_START + timedelta(days=929))["ref"] == "Genesis 1"


def test_api_today(client):
    r = client.get("/api/calendar/today", params={"date": "2026-11-14", "diaspora": 0}).json()
    assert r["hebrew"]["text"] == "ד׳ כסלו התשפ״ז" and r["parasha"]["he"] == "תולדות"
    assert r["schedule"] == "israel" and r["is_shabbat"] and "הלכה" in r["note"]
    assert r["daily"]["goto"].count(" ") >= 1 and isinstance(r["daily"]["in_library"], bool)
    assert client.get("/api/calendar/today", params={"date": "2026-11-14", "diaspora": 1}).json()["schedule"] == "diaspora"
    assert client.get("/api/calendar/today").status_code == 200


def test_api_week_and_errors(client):
    w = client.get("/api/calendar/week", params={"date": "2026-11-11"}).json()
    assert w["start"] == "2026-11-08" and len(w["days"]) == 7 and w["days"][6]["is_shabbat"]
    assert w["parasha"]["en"] == "Toldot"
    assert client.get("/api/calendar/today", params={"date": "garbage"}).status_code == 400
    assert client.get("/api/calendar/today", params={"date": "1500-01-01"}).status_code == 400


def test_genesis_in_fixture_library(client):
    r = client.get("/api/calendar/today", params={"date": "2025-01-01"}).json()
    assert r["daily"]["ref"] == "Genesis 1" and r["daily"]["in_library"] is True
