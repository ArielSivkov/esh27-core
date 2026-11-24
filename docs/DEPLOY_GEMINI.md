# מדריך פריסה ל-esh27.com, בשביל ג'מיני (וכל מנוע אחר)

נכתב בידי Claude (המלקט), 24.11.2026, מתוך הפריסה של kelim.esh27.com, שעבדה בפעם הראשונה. המטרה: אתר חדש עולה בלי לשבור אף אתר אחר, ותמיד יש דרך חזרה.

---

## 0. לפני הכול: מותר?

- **מותר רק אם אריאל אמר "כן" במפורש** לאתר הזה ולכתובת הזו. לפי כתב השליחות, שינוי DNS ופרסום פומבי חדש דורשים אישור.
- **לא בשבת ולא בחג.** פריסה מתחילה רק במוצאי שבת, מ-18:30.
- **בלי כסף.** לא פותחים מנוי, לא קונים תעודה ולא מפעילים מוצר בתשלום. אם נראה שצריך, עוצרים ושואלים.
- **בלי פרטים אישיים באתר ציבורי.** אין שמות של אנשים, סכומים, טלפונים, מיילים, מספרי מסמכים או מפתחות.

## 1. הכללים שאי אפשר לעקוף

1. **אתר חדש = Worker חדש בשם `esh27-<שם>`.** לא עורכים Worker קיים של מישהו אחר.
2. **אסור לגעת** ב-Worker, ב-Route או ברשומת DNS קיימים, ובמיוחד לא ב:
   - kav.esh27.com ו-ai.esh27.com (קַו)
   - art.esh27.com
   - world.esh27.com
   - news.esh27.com
   - esh27-seo-fallback
3. **כתובת ברמה אחת בלבד:** `<שם>.esh27.com`. כתובת כמו `a.b.esh27.com` לא מכוסה בתעודה החינמית. לתתי-עמודים משתמשים בנתיבים: `<שם>.esh27.com/lab/`.
4. **תוכן הקבצים לא משתנה בזמן הפריסה.** מי שפורס רק פורס ובודק. אם צריך לשנות תוכן, מחזירים את זה למי שכתב את הקבצים.
5. **עצירה היא תוצאה טובה.** אם משהו לא תואם, עוצרים ומדווחים. לא מנחשים ולא "מתקנים בדרך".

## 2. מאיפה לוקחים את הקבצים

תמיד ממאגר git, מקומיט מסוים, ולא מענף שזז:

```
git clone --depth 20 --branch <ענף> https://github.com/ArielSivkov/<מאגר>.git
cd <מאגר> && git checkout <SHA מלא>
```

אם קיבלת רשימת `sha256` לקבצים, בדוק אותה לפני הכול. אם יש אי-התאמה, עצור.

## 3. בדיקות לפני פריסה (קריאה בלבד)

1. אין Worker בשם `esh27-<שם>` (`npx wrangler@4 deployments list --name esh27-<שם>` נכשל, או בלוח הבקרה).
2. אין רשומת DNS ל-`<שם>.esh27.com`.
3. אין Route שתופס את `<שם>.esh27.com`. Route גובר על Custom Domain, ו-esh27-seo-fallback נוטה להוסיף routes.

אם אחד מהם כבר קיים, עצור. אל תדרוס.

## 4. פריסה: הדרך המועדפת (wrangler + קבצים סטטיים)

בתיקיית האתר, `wrangler.jsonc`:

```jsonc
{
  "name": "esh27-<שם>",
  "compatibility_date": "2025-09-01",
  "assets": { "directory": "./public", "not_found_handling": "404-page" },
  "workers_dev": false,
  "preview_urls": false,
  "routes": [ { "pattern": "<שם>.esh27.com", "custom_domain": true } ]
}
```

ואז:

```
npx wrangler@4 deploy
```

- `custom_domain: true` גורם ל-Cloudflare ליצור לבד את רשומת ה-DNS ואת התעודה. לא יוצרים DNS ידנית.
- `workers_dev: false` ו-`preview_urls: false` מונעים כתובת צדדית ב-workers.dev.
- כותרות אבטחה (CSP וכו') נכנסות לקובץ `public/_headers`. תבנית: `tools/deploy-template/_headers`.

## 5. פריסה: דרך חלופית (רק API, בלי wrangler)

זו הדרך ש-kelim עלה בה, דרך ה-MCP של Cloudflare. העלאת קבצים סטטיים דורשת שם טוקן נפרד שלא עובר, ולכן:

1. בונים `worker.js` אחד שמכיל את כל הקבצים כמחרוזות. דוגמה עובדת: `sites/kelim/build-worker.mjs`.
2. `PUT /accounts/{account}/workers/scripts/esh27-<שם>` עם multipart:
   - `metadata = {"main_module":"worker.js","compatibility_date":"2025-09-01"}`
   - הקובץ `worker.js`
3. `POST /accounts/{account}/workers/scripts/esh27-<שם>/subdomain` עם `{"enabled":false,"previews_enabled":false}`
4. `PUT /accounts/{account}/workers/domains` עם `{"hostname":"<שם>.esh27.com","service":"esh27-<שם>","zone_id":"<zone של esh27.com>"}`

הדרך הזו מתאימה לאתר קטן (עד מאות KB). תמונות גדולות מגישים מ-GitHub דרך jsDelivr, נעוץ ל-SHA:

```
https://cdn.jsdelivr.net/gh/ArielSivkov/<מאגר>@<SHA>/<נתיב>
```

וצריך להוסיף `img-src https://cdn.jsdelivr.net` ל-CSP.

## 6. בדיקות אחרי פריסה (חכה עד 5 דקות לתעודה)

1. `curl -sI https://<שם>.esh27.com/` מחזיר 200, וכותרת ה-CSP קיימת.
2. הכותרת `<title>` היא מה שצריך להיות.
3. כל עמוד ברשימה מחזיר 200, ו-`/nope` מחזיר 404.
4. כתובת workers.dev לא מגישה את האתר.
5. אין Route אחר על הכתובת. אם esh27-seo-fallback הוסיף אחד, מדווחים ולא מוחקים בלי אריאל.
6. בטלפון: אין גלילה לרוחב, הטקסט קריא, והתמונות עולות.

אם בדיקה 1–3 נכשלה, חוזרים למצב קודם (סעיף 7) ומדווחים.

## 7. חזרה למצב קודם

```
npx wrangler@4 delete esh27-<שם>
```

או `DELETE /accounts/{account}/workers/scripts/esh27-<שם>?force=true`.

הפעולה מוחקת את ה-Worker ואת ה-Custom Domain שלו, ולא נוגעת בשום דבר אחר.

## 8. תיעוד (חובה)

- בתיקיית האתר כותבים `DEPLOYED.md`, ובו:
  - תאריך
  - מי פרס
  - deployment id
  - SHA של הקבצים
  - מה נבדק
  - איך חוזרים למצב קודם
- שולחים לאריאל דיווח בעברית, עד 5 שורות: הצליח או נכשל, הקישור, הבדיקות במילה אחת לכל בדיקה, וכל דבר חריג.

## 9. טעויות נפוצות שכדאי להימנע מהן

- **פריסה מענף שזז** במקום מ-SHA. בפעם הבאה עולים קבצים אחרים.
- **יצירת DNS ידנית** ואחר כך Custom Domain. נוצרת התנגשות. משאירים ל-Custom Domain ליצור את ה-DNS.
- **שכחה לכבות workers.dev.** האתר נשאר זמין גם בכתובת צדדית, שחושפת את שם החשבון.
- **Route ישן** (למשל של esh27-seo-fallback) שגובר על ה-Custom Domain ומגיש robots.txt או sitemap אחרים.
- **"תיקון" של תוכן בזמן הפריסה.** כך דולפים פרטים, או נשבר עיצוב שנבדק.
- **הכרזה על הצלחה בלי בדיקות 1–6.**
