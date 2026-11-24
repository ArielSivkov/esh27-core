# כֵּלִים · יומן פריסה

| תאריך | מה | פרטים |
|---|---|---|
| 24.11.2026 | v0 עלה ל-https://kelim.esh27.com | Claude (סשן "8K אמנות ענן") פרס בעצמו לבקשת אריאל ("העלאות מותר לך לעשות"). Worker `esh27-kelim`, deployment `100b4ed872774cde9f574728b4f497b9`, worker.js sha256 `a86510477f3ff205…`. workers.dev וכתובות תצוגה כבויים. Custom Domain עם תעודה. דף הבית נבדק דרך Browser Rendering: הכותרת "כֵּלִים". |
| 24.11.2026 | v0.1: נוסף /art/ | היצירה 'אורות דתוהו בכלים דתיקון' בגרסה ציבורית (שמות פרטיים בלבד, בלי חשיפות אבטחה), באישור אריאל. אריחים ב-sites/kelim/art-tiles (קומיט 56cff77) מוגשים דרך jsDelivr. deployment `2b555fae4b3d48c099b14f7483a369dd`, worker.js sha256 `bf3217ee130650ef…`. נבדק דרך Browser Rendering שהתמונות נטענות. |

## מה יש באתר
- `/`: דף הבית (מספרים ותוויות כלליות בלבד), `/or/`: לוחות ההשראה של אשדוד (התמונות מ-jsDelivr, נעוצות לקומיט 07c3c0c של codesandbox-template-nuxt)
- `/art/`: היצירה ב-8K עם הגדלה (גרסה ציבורית)
- `/continue.txt`, `/kelim.json`: לכל מופע שמתעורר

## חזרה למצב קודם
מחיקת ה-Worker מוחקת גם את ה-Custom Domain, ולא נוגעת בשום דבר אחר:
`DELETE /accounts/{account}/workers/scripts/esh27-kelim?force=true` (או `npx wrangler@4 delete esh27-kelim`).

## איך מעדכנים
עורכים קבצים ב-`public/`, מריצים `node build-worker.mjs`, ופורסים את `worker.js` (PUT ל-scripts/esh27-kelim עם metadata `{main_module:"worker.js", compatibility_date:"2025-09-01"}`).
