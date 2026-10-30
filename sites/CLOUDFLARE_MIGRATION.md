# מעבר מ-Hostinger ל-Cloudflare (חינם)

ההחלטה מ-30.10.2026: את חבילת האחסון ב-Hostinger לא מחדשים. היא פגה ב-**2.11.2026**. הדומיין esh27.com נשאר רשום ב-Hostinger, ושולם עד 2.11.2027. האתרים עוברים ל-Cloudflare Pages, ולוח היזם עובר ל-Cloudflare Workers (ריפו 27Devs, ‏`developer-hub/web/hub-cf`).

המלאי המלא נמצא ב-27Devs, בקובץ `developer-hub/agent/HOSTINGER_INVENTORY.md`.

## שלב 1: גיבוי (לפני 2.11)

הסשן המקומי מגבה את כל הקבצים ואת מסד הנתונים לתיקייה `C:\27Devs\_hostinger_backup_2026-10-30\`. התיקייה הזאת לא נכנסת ל-git, כי יש בה סודות.

## שלב 2: העתקת האתרים הסטטיים לריפו

```bash
scripts/import-hostinger-backup.sh /c/27Devs/_hostinger_backup_2026-10-30
git status   # לעבור על הקבצים לפני קומיט
```

הסקריפט מעתיק 11 תתי-דומיינים: shuru, ‏farms, ‏neomi, ‏jaale, ‏danda, ‏game, ‏academy, ‏status, ‏books, ‏news ו-security. כל אחד נכנס ל-`sites/<name>/`. הסקריפט משאיר בחוץ קבצי PHP, ‏`.htaccess`, ‏`default.php` של Hostinger וכל דבר שנראה כמו סוד, ומדפיס רשימה של מה שדילג עליו.

## שלב 3: Cloudflare Pages

1. ב-Cloudflare: My Profile → API Tokens → Create Token. תבנית "Edit Cloudflare Workers", ומוסיפים הרשאת **Cloudflare Pages: Edit**.
2. ב-GitHub, בריפו הזה: Settings → Secrets → Actions. מוסיפים `CLOUDFLARE_API_TOKEN` ו-`CLOUDFLARE_ACCOUNT_ID`. ה-Account ID מופיע בצד ימין של הדשבורד.
3. דחיפה ל-main (או הרצה ידנית של "Deploy sites to Cloudflare Pages"). כל אתר עולה בכתובת `esh27-<name>.pages.dev`. בודקים שם כל אתר.

## שלב 4: DNS ל-Cloudflare (רק אחרי שכל האתרים נבדקו ב-pages.dev)

1. ב-Cloudflare: Add a site → ‏`esh27.com` → מסלול Free. Cloudflare סורק את הרשומות הקיימות. **בודקים שהן הועתקו**, במיוחד את רשומות הדואר:
   - `MX esh27.com → mx1.hostinger.com` ו-`mx2.hostinger.com`, עם אותן עדיפויות כמו ב-hPanel.
   - `TXT esh27.com → v=spf1 include:_spf.mail.hostinger.com ~all`
   - רשומות DKIM ו-DMARC, אם קיימות ב-hPanel (בדרך כלל `hostingermail-a._domainkey` וכדומה).
   - `TXT google-site-verification=...`
2. ב-hPanel → Domains → esh27.com → DNS / Nameservers. מחליפים את `ns1/ns2.dns-parking.com` בשני שרתי השמות ש-Cloudflare נותן. זה היחיד ששונה ב-Hostinger.
3. בכל פרויקט Pages: Custom domains → מוסיפים `<name>.esh27.com`. Cloudflare יוצר את ה-CNAME לבד.
4. בודקים: כל תת-דומיין עולה, ושולחים מייל ל-`ariel@esh27.com` ומקבלים אותו.

## שלב 5: esh27.com עצמו (WordPress)

את WordPress אי אפשר להריץ ב-Pages. בחזית יש כבר `index.html` סטטי (31KB), ואותו מעלים כפרויקט `esh27-portal` עם הדומיין `esh27.com`. את תוכן ה-WordPress (מסד של 13MB) ממירים לסטטי, למשל עם התוסף Simply Static, לפני 2.11, או מוותרים עליו. **החלטה של אריאל.** גם `vrf/api.php` ו-`tikkun.php` לא ירוצו. צריך להחליט מה מהם נחוץ.

## הדואר (עד 2.12.2026)

תיבת `ariel@esh27.com` נמצאת ב-Hostinger, בהזמנה נפרדת של Premium Business Email שפגה ב-**2.12.2026**. אפשרות חינמית: **Cloudflare Email Routing**, שמעביר כל מייל לכתובת הזו אל Gmail, ומ-Gmail אפשר גם לשלוח בשם `ariel@esh27.com`. לפני המעבר מייצאים את 69 ההודעות (IMAP), ורק אז מחליפים את רשומות ה-MX.

## Firebase

ה-workflow `deploy-hosting.yml` וקבצי `firebase.json` / `.firebaserc` הם הטיוטה הקודמת ל-Firebase. אם Cloudflare נבחר סופית, מוחקים אותם לפני המיזוג ל-main, כדי שלא ירוצו שתי פריסות.
