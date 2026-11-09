# telegram-hub — שלב 1: בוט טלגרם ← Google Drive (תיקיית D&A)

שולחים קובץ לבוט (או משיבים `/save` על הודעה עם קובץ) ← הקובץ נשמר בתיקיית **D&A** בדרייב
בשם `YYYY-MM-DD_<שם מקורי>.<סיומת>` ← הבוט משיב בשקט: `📂 <קישור>`.

פקודות: `/save` · `/status` בלבד. כל השאר מתעלם. משתמשים/צ'אטים שלא ברשימה — מתעלמים בשקט.
מגבלה: **20MB לקובץ** (מגבלת Bot API). גדול יותר ← הודעה "העלו ישירות לדרייב".

---

## הגדרה מהטלפון (שלב-שלב)

### 1. BotFather
1. בטלגרם ← `@BotFather` ← `/revoke` ← בחרו את הבוט ← קבלו **טוקן חדש** (הישן מת).
2. `/setprivacy` ← הבוט ← **Disable** (כדי שיראה קבצים בקבוצה בלי תיוג).
3. את הטוקן **לא** מדביקים בצ'אט ולא בקוד — רק בשלב 3.

### 2. גישה לדרייב (בחרו אחת)
- **אפשרות A (מומלץ ל-My Drive):** OAuth של אריאל ← `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` (scope: `drive.file` או `drive`).
- **אפשרות B:** Service Account ← `GOOGLE_SERVICE_ACCOUNT_JSON`.
  ⚠️ Service Account אין לו נפח אחסון ב-My Drive — עובד רק אם D&A נמצאת ב-**Shared Drive** ושיתפתם אליה את המייל של ה-SA כעורך.

### 3. סודות (אריאל מקליד, אחד-אחד)
```bash
cd telegram-hub
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put WEBHOOK_SECRET        # מחרוזת אקראית ארוכה שתמציאו
npx wrangler secret put ALLOWED_CHAT_IDS      # למשל: -1001234567890,123456789
npx wrangler secret put ALLOWED_USER_IDS      # ה-from.id של אריאל (ואחר כך שותפים)
# אפשרות A:
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put GOOGLE_REFRESH_TOKEN
# או אפשרות B:
npx wrangler secret put GOOGLE_SERVICE_ACCOUNT_JSON
```
`DRIVE_FOLDER_ID` (תיקיית D&A) כבר ב-`wrangler.toml` — הוא לא סוד.

> שימו לב: הודעה פרטית לבוט = chat_id שווה ל-from.id. לכן הכניסו את ה-ID שלכם **לשתי** הרשימות.

### 4. פריסה
```bash
npx wrangler deploy
```

### 5. חיבור ה-webhook (פעם אחת, מהמחשב/טרמינל)
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d url="https://telegram-hub.<subdomain>.workers.dev/" \
  -d secret_token="<WEBHOOK_SECRET>" \
  -d 'allowed_updates=["message"]'
```
בדיקה: שלחו `/status` לבוט ← אמור לענות `Drive: מחובר ✅`.

---

## בדיקות
```bash
npm test     # Node 18+, ללא תלויות; Telegram ו-Drive מדומים
```

## אבטחה
- אין טוקנים בקוד. הכל דרך `wrangler secret`.
- כל בקשה נבדקת מול כותרת `X-Telegram-Bot-Api-Secret-Token`.
- רשימה לבנה כפולה: chat_id **וגם** from.id.
- שותפים מתווספים ל-`ALLOWED_USER_IDS` רק אחרי שאריאל עדכן אותם.
