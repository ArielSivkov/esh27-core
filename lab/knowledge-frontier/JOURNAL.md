# יומן ריצות – נוצר אוטומטית

הקובץ נבנה מחדש מ-`runs/*/manifest.json` בכל ריצה (`infra/labrun.py index`). לא לערוך ידנית.
כל ריצה נרשמת, גם כישלון. ההשערה והקריטריון נשמרים בקומיט נפרד לפני שהריצה מתחילה.

| התחלה (UTC) | ריצה | מצב | משך | עמידה בקריטריון | השערה | תוצאה |
|---|---|---|---|---|---|---|
| 2026-11-24T00:05:53Z | `20261124T000553Z-cost-per-experiment-9050` | ok | 0.0s | pass | Speed and cost per SEAL experiment can be derived from seal/arms_resu… | T4 3.3 min/round vs CPU 25.5-60.0 (x7.7-x18.0); <= 180 runs/week on t… |
| 2026-11-24T00:05:53Z | `20261124T000553Z-host-probe-752f` | ok | 0.5s | fail | The GPU and data hosts used by earlier sessions (api.kaggle.com, hugg… | 3 reachable, 9 blocked: api.kaggle.com, www.kaggle.com, huggingface.c… |
| 2026-11-24T00:05:54Z | `20261124T000554Z-offline-verification-3053` | ok | 0.7s | pass | The committed lab reproduces every number in infra/expected.json offl… | 14 pass, 0 fail, 0 skipped (Python 3.13.18) |
| 2026-11-24T00:05:56Z | `20261124T000555Z-infra-test-suites-56b2` | failed | 11.2s | fail | Scanner and labrun behave as specified: 13 credential kinds caught, n… |  |
