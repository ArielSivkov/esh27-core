# calendar (לוח לימוד)

Routes: `GET /api/calendar/today?diaspora=0|1&date=YYYY-MM-DD`, `GET /api/calendar/week?...`. UI: `#/calendar`.

- Hebrew date: own arithmetic implementation (no runtime dependency), supported range 1900-2200.
- Parasha schedule (Israel / diaspora): Bromberg's algorithm, implemented in `bhm/features/calendar.py`.
- Verification: the tests compare every day and Shabbat 2000-2060 against `pyluach` 2.3.0 (`pip install pyluach`);
  that test is skipped if pyluach is not installed. pyluach is NOT needed at runtime.
- Daily plan: one Tanakh chapter per day (929 chapters), day 1 = 2025-01-01 = Genesis 1, repeating cycle.
  It is an automatic suggestion, not a halachic ruling.
- Parasha ranges are fixed Torah refs (no DB access); links use `#/goto/<first ref>`.
- Limitations: no holidays/fast days beyond marking a yom-tov Shabbat; no haftarah, no Daf Yomi.
