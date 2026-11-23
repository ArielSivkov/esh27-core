import json
a4=json.load(open("append4.json")); start=8127+len(a4[0]["insertText"]["text"])
head="רשומה 5 · 23.11.2026, 13:10 · מקור עדכני: נתוני arXiv עד אוקטובר 2026"
paras=[
("מה נעשה. ","נמצא עותק ציבורי ועדכני של מטא-הנתונים של arXiv ב-Hugging Face (librarian-bots/arxiv-metadata-snapshot, עודכן ב-27.10.2026). נקראו ממנו רק המזהה והקטגוריות: 3,224,542 מאמרים, האחרון 2610.31672. מעכשיו זה המקור הראשי, וכל משמרת יכולה למשוך אותו מחדש תוך כדקה. על 1,225,056 המאמרים של 2022–2026 הורץ מבחן ה-IPF הסימטרי מרשומה 4, מול התקופה עד 2021."),
("ממצאים (חישוב, יחס בפועל/צפוי לפי IPF; קודם עד 2021 ← אחר כך 2022–2026). ","שפה + למידת מכונה + פיזיקה חברתית: 0.12 ← 1.02 (התמלא, אבל עם תוחלת קטנה של 8.8). אנליזה מרוכבת + גאומטריה דיפרנציאלית + הסתברות: 0.19 ← 0.59 (התמלא חלקית; 20 מאמרים מול 34 צפויים). מכניקה סטטיסטית + ביופיזיקה + קוונטים: 0.17 ← 0.10 (נשאר חלול ואף העמיק; 10 מול 102). קומבינטוריקה + תורת המספרים + תורת ההצגות: 0.10 ← 0.12 (נשאר; 52 מול 419). ביופיזיקה + מדעי המוח החישוביים + ביולוגיה כמותית: 0.11 ← 0.13 (נשאר). אבטחה + למידת מכונה + קוונטים: 0.62 ← 1.28 (רגיל, ועכשיו מלא). ביקורת: בינה מלאכותית + למידת מכונה + למידה סטטיסטית: 0.91 ← 0.97 (רגיל, כצפוי)."),
("המסקנה. ","מכניקה סטטיסטית + ביופיזיקה + קוונטים הוא החור העקשן ביותר: חלול בכל בדיקה, בשתי הנוסחאות, ובנתונים עד 2026. גם שני החורים בתוך המתמטיקה ובביולוגיה החישובית יציבים."),
("מה לא אומת. ","OpenAlex עדיין חסום. לכן עדיין אין מדעי הרוח, הנדסה, משפט וכו'. העותק של arXiv מתעדכן בערך פעם בחודש ולא יומית."),
("הצעד הבא. ","להריץ את מבחן הזמן המלא (כל המשולשים, IPF, חלון עבר 2017–2021 מול עתיד 2022–2026) על המקור החדש, ולנסח שאלה מחקרית לחור העקשן ביותר על סמך המאמרים שלו מ-2022–2026."),
]
text="\n"+head; rng=[]; idx=start+1+len(head); hr=(start+1,idx)
for lab,body in paras:
    s=idx+1; text+="\n"+lab+body; rng.append((s,s+len(lab),s+len(lab)+len(body))); idx=rng[-1][2]
req=[{"insertText":{"location":{"index":start},"text":text}},
 {"updateParagraphStyle":{"range":{"startIndex":hr[0],"endIndex":hr[1]},"paragraphStyle":{"namedStyleType":"HEADING_3","direction":"RIGHT_TO_LEFT"},"fields":"namedStyleType,direction"}},
 {"updateParagraphStyle":{"range":{"startIndex":rng[0][0],"endIndex":rng[-1][2]},"paragraphStyle":{"namedStyleType":"NORMAL_TEXT","direction":"RIGHT_TO_LEFT"},"fields":"namedStyleType,direction"}},
 {"updateTextStyle":{"range":{"startIndex":rng[0][0],"endIndex":rng[-1][2]},"textStyle":{"bold":False},"fields":"bold"}},
 {"updateTextStyle":{"range":{"startIndex":hr[0],"endIndex":hr[1]},"textStyle":{"bold":True},"fields":"bold"}}]
for s,m,e in rng: req.append({"updateTextStyle":{"range":{"startIndex":s,"endIndex":m},"textStyle":{"bold":True},"fields":"bold"}})
print(json.dumps(req))
