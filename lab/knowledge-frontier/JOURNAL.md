# יומן ריצות – נוצר אוטומטית

הקובץ נבנה מחדש מ-`runs/*/manifest.json` בכל ריצה (`infra/labrun.py index`). לא לערוך ידנית.
כל ריצה נרשמת, גם כישלון. ההשערה והקריטריון נשמרים בקומיט נפרד לפני שהריצה מתחילה.

| התחלה (UTC) | ריצה | מצב | משך | עמידה בקריטריון | השערה | תוצאה |
|---|---|---|---|---|---|---|
| 2026-11-24T00:05:53Z | `20261124T000553Z-cost-per-experiment-9050` | ok | 0.0s | pass | Speed and cost per SEAL experiment can be derived from seal/arms_resu… | T4 3.3 min/round vs CPU 25.5-60.0 (x7.7-x18.0); <= 180 runs/week on t… |
