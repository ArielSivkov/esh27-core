"""calendar: Hebrew date, weekly parasha (Israel / diaspora) and a chapter-a-day Tanakh plan.

Pure python, no dependencies. The Hebrew date uses the standard arithmetic calendar
(Dershowitz-Reingold fixed days); the parasha schedule follows the algorithm of
Dr. Irv Bromberg (same as the pyluach package, which the tests use as an oracle when installed).
Nothing here is a halachic ruling; the daily study plan is an automatic suggestion only.
"""
from __future__ import annotations

from collections import deque
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException

NAV = {"label": "לוח לימוד", "href": "#/calendar"}

HEBREW_EPOCH = -1373427  # fixed day (date.toordinal() scale) of 1 Tishrei 1 AM


# ---------------------------------------------------------------- Hebrew calendar
def is_leap(y: int) -> bool:
    return (7 * y + 1) % 19 < 7


def _elapsed(y: int) -> int:
    months = (235 * y - 234) // 19
    parts = 12084 + 13753 * months
    days = 29 * months + parts // 25920
    return days + 1 if (3 * (days + 1)) % 7 < 3 else days


def new_year(y: int) -> int:
    n0, n1, n2 = _elapsed(y - 1), _elapsed(y), _elapsed(y + 1)
    corr = 2 if n2 - n1 == 356 else (1 if n1 - n0 == 382 else 0)
    return HEBREW_EPOCH + n1 + corr


def year_days(y: int) -> int:
    return new_year(y + 1) - new_year(y)


def month_order(y: int) -> list[int]:
    """Month numbers in year order. Nisan=1 ... Elul=6, Tishrei=7 ... Adar=12, Adar II=13 (leap)."""
    return [7, 8, 9, 10, 11, 12] + ([13] if is_leap(y) else []) + [1, 2, 3, 4, 5, 6]


def month_len(y: int, m: int) -> int:
    if m in (1, 3, 5, 7, 11):
        return 30
    if m in (2, 4, 6, 10):
        return 29
    if m == 8:
        return 30 if year_days(y) % 10 == 5 else 29
    if m == 9:
        return 29 if year_days(y) % 10 == 3 else 30
    if m == 12:
        return 30 if is_leap(y) else 29
    return 29  # 13: Adar II


def fixed_to_hebrew(d: int) -> tuple[int, int, int]:
    y = (d - HEBREW_EPOCH) * 98496 // 35975351 + 1
    while new_year(y + 1) <= d:
        y += 1
    while new_year(y) > d:
        y -= 1
    off = d - new_year(y)
    for m in month_order(y):
        ml = month_len(y, m)
        if off < ml:
            return y, m, off + 1
        off -= ml
    raise ValueError("date out of range")


def hebrew_to_fixed(y: int, m: int, d: int) -> int:
    n = new_year(y) + d - 1
    for mm in month_order(y):
        if mm == m:
            return n
        n += month_len(y, mm)
    raise ValueError("bad month")


MONTHS_HE = {1: "ניסן", 2: "אייר", 3: "סיוון", 4: "תמוז", 5: "אב", 6: "אלול", 7: "תשרי", 8: "חשוון",
             9: "כסלו", 10: "טבת", 11: "שבט", 12: "אדר", 13: "אדר ב׳"}
MONTHS_EN = {1: "Nisan", 2: "Iyar", 3: "Sivan", 4: "Tammuz", 5: "Av", 6: "Elul", 7: "Tishrei", 8: "Cheshvan",
             9: "Kislev", 10: "Tevet", 11: "Shevat", 12: "Adar", 13: "Adar II"}
WEEKDAYS_HE = ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "שבת קודש", "יום ראשון"]  # by date.weekday()

_ONES = ["", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט"]
_TENS = ["", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ"]
_HUND = ["", "ק", "ר", "ש", "ת", "תק", "תר", "תש", "תת", "תתק"]


def gematria(n: int) -> str:
    s = ""
    while n >= 400:
        s += "ת"
        n -= 400
    s += _HUND[n // 100]
    n %= 100
    if n in (15, 16):
        s += "טו" if n == 15 else "טז"
    else:
        s += _TENS[n // 10] + _ONES[n % 10]
    return s + "׳" if len(s) == 1 else s[:-1] + "״" + s[-1]


def year_he(y: int) -> str:
    """5787 -> התשפ״ז (thousands written as ה, as is customary)."""
    return "ה" + gematria(y % 1000)


def hebrew_date(d: date) -> dict:
    y, m, day = fixed_to_hebrew(d.toordinal())
    mname = MONTHS_HE[m]
    if m == 12 and is_leap(y):
        mname = "אדר א׳"
    return {"year": y, "month": m, "day": day, "leap": is_leap(y), "month_he": mname, "month_en": MONTHS_EN[m],
            "text": f"{gematria(day)} {mname} {year_he(y)}", "year_he": year_he(y)}


# ---------------------------------------------------------------- parashot
# (Hebrew, English, book, start chapter:verse, end chapter:verse)
_P = [
    ("בראשית", "Bereshit", "Genesis", "1:1", "6:8"), ("נח", "Noach", "Genesis", "6:9", "11:32"),
    ("לך לך", "Lech Lecha", "Genesis", "12:1", "17:27"), ("וירא", "Vayera", "Genesis", "18:1", "22:24"),
    ("חיי שרה", "Chayei Sara", "Genesis", "23:1", "25:18"), ("תולדות", "Toldot", "Genesis", "25:19", "28:9"),
    ("ויצא", "Vayetzei", "Genesis", "28:10", "32:3"), ("וישלח", "Vayishlach", "Genesis", "32:4", "36:43"),
    ("וישב", "Vayeshev", "Genesis", "37:1", "40:23"), ("מקץ", "Miketz", "Genesis", "41:1", "44:17"),
    ("ויגש", "Vayigash", "Genesis", "44:18", "47:27"), ("ויחי", "Vayechi", "Genesis", "47:28", "50:26"),
    ("שמות", "Shemot", "Exodus", "1:1", "6:1"), ("וארא", "Vaera", "Exodus", "6:2", "9:35"),
    ("בא", "Bo", "Exodus", "10:1", "13:16"), ("בשלח", "Beshalach", "Exodus", "13:17", "17:16"),
    ("יתרו", "Yitro", "Exodus", "18:1", "20:23"), ("משפטים", "Mishpatim", "Exodus", "21:1", "24:18"),
    ("תרומה", "Terumah", "Exodus", "25:1", "27:19"), ("תצוה", "Tetzaveh", "Exodus", "27:20", "30:10"),
    ("כי תשא", "Ki Tisa", "Exodus", "30:11", "34:35"), ("ויקהל", "Vayakhel", "Exodus", "35:1", "38:20"),
    ("פקודי", "Pekudei", "Exodus", "38:21", "40:38"), ("ויקרא", "Vayikra", "Leviticus", "1:1", "5:26"),
    ("צו", "Tzav", "Leviticus", "6:1", "8:36"), ("שמיני", "Shmini", "Leviticus", "9:1", "11:47"),
    ("תזריע", "Tazria", "Leviticus", "12:1", "13:59"), ("מצורע", "Metzora", "Leviticus", "14:1", "15:33"),
    ("אחרי מות", "Achrei Mot", "Leviticus", "16:1", "18:30"), ("קדושים", "Kedoshim", "Leviticus", "19:1", "20:27"),
    ("אמור", "Emor", "Leviticus", "21:1", "24:23"), ("בהר", "Behar", "Leviticus", "25:1", "26:2"),
    ("בחוקותי", "Bechukotai", "Leviticus", "26:3", "27:34"), ("במדבר", "Bamidbar", "Numbers", "1:1", "4:20"),
    ("נשא", "Nasso", "Numbers", "4:21", "7:89"), ("בהעלותך", "Beha'alotcha", "Numbers", "8:1", "12:16"),
    ("שלח", "Shlach", "Numbers", "13:1", "15:41"), ("קרח", "Korach", "Numbers", "16:1", "18:32"),
    ("חקת", "Chukat", "Numbers", "19:1", "22:1"), ("בלק", "Balak", "Numbers", "22:2", "25:9"),
    ("פינחס", "Pinchas", "Numbers", "25:10", "30:1"), ("מטות", "Matot", "Numbers", "30:2", "32:42"),
    ("מסעי", "Masei", "Numbers", "33:1", "36:13"), ("דברים", "Devarim", "Deuteronomy", "1:1", "3:22"),
    ("ואתחנן", "Vaetchanan", "Deuteronomy", "3:23", "7:11"), ("עקב", "Eikev", "Deuteronomy", "7:12", "11:25"),
    ("ראה", "Re'eh", "Deuteronomy", "11:26", "16:17"), ("שופטים", "Shoftim", "Deuteronomy", "16:18", "21:9"),
    ("כי תצא", "Ki Teitzei", "Deuteronomy", "21:10", "25:19"), ("כי תבוא", "Ki Tavo", "Deuteronomy", "26:1", "29:8"),
    ("נצבים", "Nitzavim", "Deuteronomy", "29:9", "30:20"), ("וילך", "Vayeilech", "Deuteronomy", "31:1", "31:30"),
    ("האזינו", "Ha'Azinu", "Deuteronomy", "32:1", "32:52"), ("וזאת הברכה", "Vezot Haberakhah", "Deuteronomy", "33:1", "34:12"),
]
VAYAKHEL, TAZRIA, ACHAREI, BEHAR, CHUKAT, MATOT, NITZAVIM = 21, 26, 28, 31, 38, 41, 50


def _wd(fixed: int) -> int:
    """Weekday of a fixed day: 0=Sunday .. 6=Shabbat."""
    return fixed % 7


def _parshaless(m: int, d: int, israel: bool) -> bool:
    if israel and (m, d) in [(7, 23), (1, 22), (3, 7)]:
        return False
    if m == 7 and (d in (1, 2, 10) or 15 <= d <= 23):
        return True
    if m == 1 and 15 <= d <= 22:
        return True
    return m == 3 and d in (6, 7)


_TABLES: dict = {}


def _table(year: int, israel: bool) -> dict:
    """fixed day of each Shabbat of the Hebrew year -> parasha indexes (None = yom tov)."""
    key = (year, israel)
    if key in _TABLES:
        return _TABLES[key]
    plist = deque([51, 52] + list(range(52)))
    leap = is_leap(year)
    rh = new_year(year)
    pesach_wd = _wd(hebrew_to_fixed(year, 1, 15)) + 1  # 1=Sunday .. 7=Shabbat
    erev_pesach = hebrew_to_fixed(year, 1, 14)
    tisha = hebrew_to_fixed(year, 5, 9)
    next_rh_wd = _wd(new_year(year + 1)) + 1
    if _wd(rh) + 1 > 4:  # RH on Fri/Shabbat: Vayeilech is not read separately before it
        plist.popleft()
    shabbat = rh + (6 - _wd(rh)) % 7
    end = new_year(year + 1)
    out: dict = {}
    while shabbat < end:
        _, m, d = fixed_to_hebrew(shabbat)
        if _parshaless(m, d, israel):
            out[shabbat] = None
        else:
            p = plist.popleft()
            ps = [p]
            if ((p == VAYAKHEL and (erev_pesach - shabbat) // 7 < 3)
                    or (p in (TAZRIA, ACHAREI) and not leap)
                    or (p == BEHAR and not leap and (not israel or pesach_wd != 7))
                    or (p == CHUKAT and not israel and pesach_wd == 5)
                    or (p == MATOT and (tisha - shabbat) // 7 < 2)
                    or (p == NITZAVIM and next_rh_wd > 4)):
                ps.append(plist.popleft())
            out[shabbat] = ps
        shabbat += 7
    if len(_TABLES) > 40:
        _TABLES.clear()
    _TABLES[key] = out
    return out


def _holiday_he(m: int, d: int) -> str:
    if m == 7 and d <= 2:
        return "ראש השנה"
    if m == 7 and d == 10:
        return "יום הכיפורים"
    if m == 7:
        return "סוכות / שמיני עצרת"
    if m == 1:
        return "פסח"
    return "שבועות"


def parasha_for(d: date, israel: bool = True) -> dict:
    """Parasha of the Shabbat on or after `d` (a yom tov Shabbat has none: `holiday` is set)."""
    fx = d.toordinal()
    shab = fx + (6 - _wd(fx)) % 7
    hy, hm, hd = fixed_to_hebrew(shab)
    idx = _table(hy, israel).get(shab)
    sdate = date.fromordinal(shab).isoformat()
    if idx is None:
        return {"shabbat": sdate, "indexes": [], "he": None, "en": None, "ranges": [], "range": None,
                "goto": None, "holiday": _holiday_he(hm, hd)}
    parts = [_P[i] for i in idx]
    first, last = parts[0], parts[-1]
    return {"shabbat": sdate, "indexes": idx, "he": ", ".join(p[0] for p in parts),
            "en": ", ".join(p[1] for p in parts),
            "ranges": [f"{p[2]} {p[3]}-{p[4]}" for p in parts],
            "range": f"{first[2]} {first[3]}-{last[4]}" if len(parts) == 1 or first[2] == last[2]
            else f"{first[2]} {first[3]} - {last[2]} {last[4]}",
            "goto": f"{first[2]} {first[3]}", "holiday": None}


# ---------------------------------------------------------------- Tanakh chapter-a-day
TANAKH = [
    ("Genesis", "בראשית", 50), ("Exodus", "שמות", 40), ("Leviticus", "ויקרא", 27), ("Numbers", "במדבר", 36),
    ("Deuteronomy", "דברים", 34), ("Joshua", "יהושע", 24), ("Judges", "שופטים", 21), ("I Samuel", "שמואל א", 31),
    ("II Samuel", "שמואל ב", 24), ("I Kings", "מלכים א", 22), ("II Kings", "מלכים ב", 25), ("Isaiah", "ישעיהו", 66),
    ("Jeremiah", "ירמיהו", 52), ("Ezekiel", "יחזקאל", 48), ("Hosea", "הושע", 14), ("Joel", "יואל", 4),
    ("Amos", "עמוס", 9), ("Obadiah", "עובדיה", 1), ("Jonah", "יונה", 4), ("Micah", "מיכה", 7),
    ("Nahum", "נחום", 3), ("Habakkuk", "חבקוק", 3), ("Zephaniah", "צפניה", 3), ("Haggai", "חגי", 2),
    ("Zechariah", "זכריה", 14), ("Malachi", "מלאכי", 3), ("Psalms", "תהילים", 150), ("Proverbs", "משלי", 31),
    ("Job", "איוב", 42), ("Song of Songs", "שיר השירים", 8), ("Ruth", "רות", 4), ("Lamentations", "איכה", 5),
    ("Ecclesiastes", "קהלת", 12), ("Esther", "אסתר", 10), ("Daniel", "דניאל", 12), ("Ezra", "עזרא", 10),
    ("Nehemiah", "נחמיה", 13), ("I Chronicles", "דברי הימים א", 29), ("II Chronicles", "דברי הימים ב", 36),
]
TOTAL_CHAPTERS = sum(b[2] for b in TANAKH)  # 929
PLAN_START = date(2025, 1, 1)  # day 1 of the cycle = Genesis 1; repeats every 929 days


def daily_chapter(d: date) -> dict:
    n = (d - PLAN_START).days % TOTAL_CHAPTERS
    k = n
    for title, he, ch in TANAKH:
        if k < ch:
            ref = f"{title} {k + 1}"
            return {"day_index": n + 1, "of": TOTAL_CHAPTERS, "book": title, "book_he": he, "chapter": k + 1,
                    "ref": ref, "ref_he": f"{he} {gematria(k + 1)}", "goto": ref}
        k -= ch
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- API
NOTE = "הצעת הלימוד נוצרה אוטומטית לפי מספר היום; אין בה הלכה למעשה ואינה פסיקה."


def _parse(s: str | None) -> date:
    if not s:
        d = date.today()
    else:
        try:
            d = date.fromisoformat(s)
        except ValueError:
            raise HTTPException(400, "תאריך לא תקין, יש להשתמש בפורמט YYYY-MM-DD")
    if not (date(1900, 1, 1) <= d <= date(2200, 12, 31)):
        raise HTTPException(400, "התאריך מחוץ לטווח הנתמך (1900-2200)")
    return d


def make_router(node) -> APIRouter:
    r = APIRouter()

    def in_library(title: str) -> bool:
        try:
            return node.con.execute("SELECT 1 FROM versions WHERE title=? LIMIT 1", (title,)).fetchone() is not None
        except Exception:
            return False

    def day_info(d: date) -> dict:
        daily = daily_chapter(d)
        daily["in_library"] = in_library(daily["book"])
        return {"date": d.isoformat(), "weekday_he": WEEKDAYS_HE[d.weekday()], "is_shabbat": d.weekday() == 5,
                "hebrew": hebrew_date(d), "daily": daily}

    @r.get("/api/calendar/today")
    def today(diaspora: int = 0, date: str | None = None):
        d = _parse(date)
        israel = not diaspora
        out = day_info(d)
        out["schedule"] = "israel" if israel else "diaspora"
        out["parasha"] = parasha_for(d, israel)
        out["note"] = NOTE
        return out

    @r.get("/api/calendar/week")
    def week(diaspora: int = 0, date: str | None = None):
        d = _parse(date)
        israel = not diaspora
        sunday = d - timedelta(days=(d.weekday() + 1) % 7)
        return {"schedule": "israel" if israel else "diaspora", "start": sunday.isoformat(),
                "parasha": parasha_for(sunday, israel), "days": [day_info(sunday + timedelta(days=i)) for i in range(7)],
                "note": NOTE}

    return r
