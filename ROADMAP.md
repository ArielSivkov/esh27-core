# esh27 Cloud Roadmap: 10 רמות (מ-0.1 ל-100)

| # | רמה | מטרה | סטטוס |
|---|---|---|---|
| 1 | ניקיון ואבטחה | אין סודות בקוד, `.gitignore`, README, מבנה תקין | ✅ בוצע (ראה למטה) |
| 2 | CI אוטומטי | בדיקה אוטומטית בכל Push | ✅ crown-bot, esh27-core |
| 3 | משימות מתוזמנות | uptime-monitor כל 15 דק' + התראת טלגרם | ✅ בוצע |
| 4 | פריסה לענן | esh27-core ב-Cloud Run (WIF כבר מוגדר ב-`deploy.yml`) | ⏳ דורש מיזוג ל-main + `GEMINI_API_KEY` ב-Secrets |
| 5 | מוח AI אחד | crown-bot, AI_Academic_Writer, gpt_sefaria_app פונים ל-`/v1/generate` של esh27-core | ⏳ אחרי רמה 4 |
| 6 | חיבור לעולם | הבוט קורא יומן, שולח מייל, רושם ל-Sheets, שומר ל-Drive | ⏳ |
| 7 | לוח בקרה חי | דף אחד: uptime, בוטים, מסחר, פריסות | ⏳ |
| 8 | צוות סוכנים | סוכן ענן לכל ריפו, מעקב PR ותיקון CI אוטומטי | ⏳ |
| 9 | סוכנים אוטונומיים עם בלמים | ftmo-agent-bot בדמו בלבד, kill-switch מ-`risk_management.md` | ⏳ קוד הסוכן (`src/index.ts`) עוד לא קיים |
| 10 | מטה esh27 | טלגרם = מרכז פיקוד: פקודה → בנייה → בדיקה → פריסה → דוח | ⏳ |

## מה בוצע ברמות 1–3

- **crown-bot**: טוקן טלגרם ומפתח OpenRouter הוצאו מהקוד אל משתני סביבה (`.env.example`). נוספו CI שחוסם סודות בקוד ו-README.
- **ftmo-agent-bot**: קבצים שהיו בטעות בתוך `.github/workflows` הועברו ל-`memory/`. הריצה המתוזמנת כל 30 דקות נכשלה תמיד (`dist/index.js` לא קיים) ולכן הושבתה עד שיהיה קוד.
- **esh27-core**: נוספו CI (קומפילציה ובניית Docker) ו-`.gitignore`.
- **AI_Academic_Writer**: מפתח OpenAI נקרא מ-`OPENAI_API_KEY`.
- **uptime-monitor**: סקריפט בלי תלויות, ריצה כל 15 דקות ב-GitHub Actions והתראת טלגרם.

## פעולות שרק הבעלים יכול לבצע

1. **לבטל מיד** את טוקן הטלגרם הישן (@BotFather → `/revoke`) ואת מפתח OpenRouter הישן. שניהם עדיין בהיסטוריית git.
2. להוסיף GitHub Secrets: `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_CHAT_ID`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`.
3. למזג את ענפי `ccr-de49b8e3-riprop` ל-main.
