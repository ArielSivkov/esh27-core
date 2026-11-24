# יומן ריצות – נוצר אוטומטית

הקובץ נבנה מחדש מ-`runs/*/manifest.json` בכל ריצה (`infra/labrun.py index`). לא לערוך ידנית.
כל ריצה נרשמת, גם כישלון. ההשערה והקריטריון נשמרים בקומיט נפרד לפני שהריצה מתחילה;
העמודה 'רישום מראש' אומרת אם הקומיט הזה גם נדחף לגיטהאב לפני ההרצה.

| התחלה (UTC) | ריצה | מצב | משך | עמידה בקריטריון | רישום מראש | השערה | תוצאה |
|---|---|---|---|---|---|---|---|
| 2026-11-24T00:05:53Z | `20261124T000553Z-cost-per-experiment-9050` | ok | 0.0s | pass | קומיט מקומי | Speed and cost per SEAL experiment can be derived from seal/arms_resu… | T4 3.3 min/round vs CPU 25.5-60.0 (x7.7-x18.0); <= 180 runs/week on t… |
| 2026-11-24T00:05:53Z | `20261124T000553Z-host-probe-752f` | ok | 0.5s | fail | קומיט מקומי | The GPU and data hosts used by earlier sessions (api.kaggle.com, hugg… | 3 reachable, 9 blocked: api.kaggle.com, www.kaggle.com, huggingface.c… |
| 2026-11-24T00:05:54Z | `20261124T000554Z-offline-verification-3053` | ok | 0.7s | pass | קומיט מקומי | The committed lab reproduces every number in infra/expected.json offl… | 14 pass, 0 fail, 0 skipped (Python 3.13.18) |
| 2026-11-24T00:05:56Z | `20261124T000555Z-infra-test-suites-56b2` | failed | 11.2s | fail | קומיט מקומי | Scanner and labrun behave as specified: 13 credential kinds caught, n… |  |
| 2026-11-24T00:06:27Z | `20261124T000626Z-infra-test-suites-2d8e` | ok | 11.2s | pass | קומיט מקומי | Same as run 20261124T000555Z-infra-test-suites-56b2, after fixing the… |  |
| 2026-11-24T01:09:01Z | `20261124T010901Z-cost-per-experiment-v2-c58c` | ok | 0.0s | pass | קומיט מקומי | Re-derivation after the red team: the same-config T4/CPU ratio and th… | T4 vs CPU, same config: x7.7 per round (x7.0-x8.5), x5.1 whole run; ~… |
| 2026-11-24T01:09:02Z | `20261124T010902Z-host-probe-6aab` | ok | 0.6s | fail | קומיט מקומי | Kaggle and Hugging Face are reachable from this session (they were bl… | 3 reachable, 9 blocked: api.kaggle.com, www.kaggle.com, huggingface.c… |
| 2026-11-24T01:09:03Z | `20261124T010903Z-offline-verification-v2-ba52` | ok | 0.9s | pass | קומיט מקומי | After the red-team fixes the committed lab still reproduces every exp… | 16 pass, 0 fail, 0 skipped (Python 3.13.18) |
| 2026-11-24T01:09:05Z | `20261124T010904Z-infra-test-suites-v2-d616` | ok | 59.8s | pass | קומיט מקומי | Scanner, labrun (one test per red-team finding) and empty-machine boo… |  |
