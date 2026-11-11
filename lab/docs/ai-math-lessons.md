# מה למדנו ממחקר AI-for-Math (2019–2026), ואילו מסקנות אנחנו מסיקים

> מסמך רקע של ESH27 Lab. עודכן לאחרונה: 2026-11-04.
> מוסכמות: מספרים ותאריכים נבדקו מול מקורות ראשוניים ככל האפשר. כל דבר שלא הצלחנו לאמת מסומן **[לא אומת]**. טענות של חברות על המוצרים שלהן נחשבות "טענת יצרן" עד שגורם חיצוני בודק אותן.

---

## תקציר בשורה אחת

בין 2019 ל-2026, AI במתמטיקה עבר מ"פותר תרגילי אולימפיאדה בסביבה פורמלית" ל"שותף שמוכיח למות מחקריות, מוצא מקורות נשכחים, משפר חסמים במשימות בנייה ואפילו מפרמל משפטים ענקיים". אבל כמעט כל הצלחה אמיתית נשענה על **מוודא (verifier)**: Lean, חישוב שאפשר לשחזר, או פונקציית ניקוד. וכמעט כל שערוריית hype נבעה מהיעדר מוודא כזה.

---

## 1. מתמטיקה פורמלית: Lean 4 ו-mathlib

| אירוע | תאריך | מה למדנו |
|---|---|---|
| **Liquid Tensor Experiment**: אתגר של Peter Scholze לפרמל משפט מרכזי מתוך condensed mathematics | האתגר: דצמבר 2020. הלמה המרכזית: יוני 2021. השלמה: יולי 2022 | קהילת Lean (בהובלת Johan Commelin) פרמלה מתמטיקה מחקרית עכשווית. Scholze כתב שהתהליך שיפר את הבנתו את ההוכחה. **Lean מתאים למחקר ולא רק לתרגילים.** |
| **הפורט ל-Lean 4** של mathlib | הושלם ביולי 2023 | מאז mathlib היא ספרייה מאוחדת, מתוחזקת היטב ובקצב צמיחה גבוה (מאות אלפי משפטים; את המספר המדויק יש לבדוק ב-[mathlib stats](https://leanprover-community.github.io/mathlib_stats.html)). |
| **PFR** (Polynomial Freiman–Ruzsa; Gowers–Green–Manners–Tao) | ההוכחה בנובמבר 2023; פורמליזציה מלאה תוך כ-3 שבועות, בדצמבר 2023 | בזכות blueprint ועבודה מבוזרת, פרויקט מחקרי חדש פורמל בתוך שבועות. **השילוב של blueprint ושיתוף פעולה פתוח הוא שיטת העבודה המנצחת.** |
| **Equational Theories Project** (Tao) | הושק בספטמבר–אוקטובר 2024 | כ-22 מיליון טענות גרירה בין 4,694 חוקים של מגמות (magmas) הוכרעו כולן, בשילוב של ATP קלאסיים (Vampire ודומיו), חיפוש מודלים, עבודה אנושית ו-Lean כ"שופט סופי". **מתמטיקה בהיקף רחב ובמיקור המונים אפשרית רק עם בדיקה פורמלית.** |
| **Strong PNT** על ידי Gauss של Math Inc. | ספטמבר 2025 | סוכן אוטו-פורמליזציה השלים בכ-3 שבועות את האתגר של Tao ו-Kontorovich (כ-25 אלף שורות). בני אדם סיפקו את ה-blueprint. ב-Zulip דווח שהסוכן לפעמים "עקף" למות שפורמלו בצורה שגויה. **צריך לבדוק את הטענות (statements), לא רק את ההוכחות.** |
| **פרויקט FLT** (Kevin Buzzard, Imperial) | מענק EPSRC לחמש שנים מאוקטובר 2024. המטרה: לצמצם את FLT לתוצאות שהיו ידועות בשנות ה-80 | ב-4 בספטמבר 2026 Anthropic דיווחה על **הוכחה מלאה ובדוקה במחשב של FLT ב-Lean**: כ-13 מיליון שורות, כ-30 אלף משפטי ביניים, כ-11 ימים של עבודת סוכני Claude, רק שלוש האקסיומות הסטנדרטיות, והטענה הסופית הושוותה ל-statement שב-mathlib. Buzzard בדק אותה, ולפי הדיווחים הגדיר אותה "תוצאה גדולה לאוטו-פורמליזציה" שמתמטית "לא מלמדת אותנו כמעט דבר חדש". (את פוסט Xena המקורי לא הצלחנו לקרוא ישירות, וציטוטי Buzzard נלקחו ממקורות משניים: **[לא אומת מילולית]**.) |

**Terence Tao** הוא הדוגמה הבולטת לחוקר מוביל שמשלב AI בעבודה: GitHub Copilot לכתיבת Lean, שימוש ב-LLM לחיפוש ספרות ולניסוח, ה-ETP, תחזוקה משותפת של ויקי "AI contributions to Erdős problems", ומאמר משותף עם AlphaEvolve (נובמבר 2025, 67 בעיות). הקו שהוא מציג באופן עקבי: **AI כ"עוזר מחקר" שהפלט שלו נבדק, ולא כאורקל.**

**Kevin Buzzard** טוען כבר שנים שהמתמטיקה המחקרית סובלת מ"הוכחות שאף אחד לא בדק באמת", ש-Lean הוא הפתרון, וש-LLMs שמייצרים הוכחות בשפה טבעית בלי פורמליזציה הם בעייתיים. הוא גם הזהיר מ-hype סביב פתרון "בעיות גדולות" בידי AI.

---

## 2. מוכיחי משפטים נוירוניים (Neural Theorem Provers)

| מערכת | תאריך | עיקר |
|---|---|---|
| **GPT-f** (Polu & Sutskever, OpenAI) | ספטמבר 2020 | מודל שפה ראשון שתרם הוכחות שהתקבלו לספרייה פורמלית (Metamath). |
| **miniF2F** (benchmark) | 2021 | 488 בעיות אולימפיאדה ב-Lean ובמערכות נוספות. **הבנצ'מרק הזה כבר רווי** (מעל 99% ב-Seed-Prover, 2025). |
| **HTPS** (Lample et al., Meta) | 2022 | חיפוש בעץ הוכחה בהשראת AlphaZero, יחד עם online training. |
| **LeanDojo / ReProver** (Yang et al.) | 2023 | כלים פתוחים, dataset מ-mathlib ו-retrieval של premises. **תשתית פתוחה מאפשרת למעבדות קטנות להשתתף.** |
| **PutnamBench** (Tsoukalas et al.) | 2024 | 600+ בעיות פטנם. בהתחלה הצלחות בודדות, ובסוף 2025 מעל 50% ([לא אומת] המספר העדכני). |
| **DeepSeek-Prover V1 / V1.5 / V2** | מאי 2024 / אוגוסט 2024 / אפריל 2025 | נתונים סינתטיים מאוטו-פורמליזציה, RL עם משוב מ-Lean. V2 (671B) הגיע ל-88.9% ב-miniF2F ול-49 בעיות ב-PutnamBench. |
| **Goedel-Prover (V1, V2)** | פברואר ואוגוסט 2025 | מודלים פתוחים קטנים יחסית עם expert iteration. **מודל קטן ומאומן היטב מתחרה במודלים ענקיים.** |
| **Kimina-Prover** (Moonshot ו-Numina) | אפריל 2025 | "whole-proof" עם RL, בסגנון reasoning model. |
| **Seed-Prover** (ByteDance) | יולי 2025 | 78.1% מבעיות IMO היסטוריות שפורמלו, מעל 50% ב-PutnamBench. ב-IMO 2025 קיבל ציון רשמי של 30 נקודות (כסף) עם פתרונות פורמליים, אחרי שהטענות פורמלו בידי בני אדם. |
| **AlphaGeometry** (DeepMind) | Nature, ינואר 2024 | מנוע סימבולי יחד עם מודל שפה שמציע בניות עזר, ואימון על נתונים סינתטיים בלבד. |
| **AlphaProof ו-AlphaGeometry 2** | יולי 2024 (IMO 2024) | 28/42, רמת מדליית כסף: 4 מתוך 6 בעיות, כולל הקשה ביותר (P6). חלק מהבעיות דרשו **ימים** של חישוב, והטענות תורגמו ל-Lean ידנית. מאמר ב-Nature פורסם ב-12 בנובמבר 2025 (אוטו-פורמליזציה של כ-80 מיליון טענות, Test-Time RL). |
| **Harmonic Aristotle** | IMO 2025 (יולי 2025); arXiv:2510.01346 | פתרונות פורמליים ב-Lean ל-5 מתוך 6 בעיות, "gold-medal-equivalent". הטענות פורמלו ידנית. מאז 2026 Aristotle משמש כ"מפרמל" של הוכחות שנכתבו בידי LLMs, למשל בבעיות ארדש. |
| **Gemini Deep Think ומודל ניסיוני של OpenAI** | יולי 2025 (IMO 2025) | 35/42 ב**שפה טבעית**, ברמת זהב. ההוכחות של Deep Think אושרו על ידי ה-IMO, ושל OpenAI נבדקו בידי מדליסטים לשעבר. **ההבדל המכריע הוא שאלה הוכחות טבעיות שבודקים אנושיים בדקו, ולא הוכחות פורמליות.** |

**מגמה מרכזית ב-2025–2026:** מודלי reasoning כלליים (סדרות GPT-5.x, Gemini Deep Think, Claude) מתקרבים למוכיחים הייעודיים, ושילוב של **LLM כללי שכותב סקיצה עם מפרמל ייעודי (Aristotle וכדומה) שסוגר ב-Lean** הפך לצנרת הסטנדרטית.

**First Proof** (1stproof.org): אתגר של מתמטיקאים בכירים עם בעיות מחקר **שלא פורסמו**. סבב 1 בפברואר 2026: המודל הטוב פתר רק בעיות בודדות. סבב 2 ביוני 2026: הטוב ביותר פתר 6 מתוך 10 (צוות ETH עם מערכת סוכנים). סבב 3 באוקטובר 2026: לפי הדיווחים, המערכות יחד פתרו את כל העשר, אבל התיעוד והתקשורת היו חלשים, ובכל ההגשות של המודלים הפתוחים היו שגיאות מהותיות ([לא אומת] מול הדוח הרשמי). **מה למדנו: מבחנים על בעיות לא מפורסמות הם הדרך היחידה להימנע מזיהום (contamination).**

---

## 3. חיפוש וגילוי: בעיות בנייה וניסוח השערות

| מערכת / עבודה | תאריך | מה עשתה | לקח |
|---|---|---|---|
| **Wagner**, "Constructions in combinatorics via neural networks" | 2021 (arXiv:2104.14516) | RL פשוט (cross-entropy method) שמצא דוגמאות נגדיות להשערות בתורת הגרפים | **שיטה זולה ופשוטה מצליחה כשיש ניקוד ברור.** |
| **Ramanujan Machine** (Raayoni et al.) | Nature, פברואר 2021 | ניסוח השערות על שברים משולבים לקבועים מתמטיים | רוב הפלט היה השערות ולא הוכחות. ערך אמיתי, אבל מוגבל. |
| **Davies et al.** (DeepMind עם Lackenby, Juhász ו-Williamson) | Nature, דצמבר 2021 | ML הצביע על קשרים: אינווריאנטים של קשרים (signature מול slope) ופולינומי Kazhdan–Lusztig | **ML כ"מיקרוסקופ" שמכוון את האינטואיציה, וההוכחה נשארת אנושית.** |
| **FunSearch** | Nature, דצמבר 2023 | LLM עם מעריך אוטומטי בלולאה אבולוציונית. מצא cap sets גדולים יותר (מימד 8: 512) ו-admissible sets | **התוצר הוא תוכנה קריאה ולא רק מספר**, ולכן אפשר להבין אותו ולהכליל ממנו. |
| **PatternBoost** (Charton, Ellenberg, Wagner, Williamson) | נובמבר 2024 | שילוב של transformer וחיפוש מקומי בבעיות קומבינטוריות | חיפוש גלובלי ומקומי משלימים זה את זה. |
| **AlphaEvolve** (DeepMind) | 14 במאי 2025 | קידוד אבולוציוני מבוסס Gemini. בכ-50 בעיות פתוחות שיחזר את ה-SOTA בכ-75% ושיפר בכ-20%. מספר נשיקה במימד 11 עלה מ-592 ל-593. כפל מטריצות מרוכבות 4×4 ב-48 כפלים (במקום 49 של Strassen) | **חיפוש אבולוציוני עם verifier מצליח בבעיות בנייה עם ניקוד, אבל השיפורים בדרך כלל שוליים.** |
| **AlphaEvolve בקנה מידה** (Georgiev, Gómez-Serrano, Tao, Wagner) | נובמבר 2025 (arXiv:2511.02864) | 67 בעיות באנליזה, קומבינטוריקה וגאומטריה | הם מתעדים הצלחות, כישלונות ו"רמאויות" של המערכת (ניצול באגים במעריך). **המעריך חייב להיות קשיח ולא ניתן לעקיפה.** |

---

## 4. פרשת בעיות ארדש: מה היה חדש באמת ומה היה גילוי מחדש של ספרות

**אוקטובר 2025:** חוקרי OpenAI הכריזו ברשתות ש-GPT-5 "פתר 10 בעיות ארדש פתוחות". Thomas Bloom, שמתחזק את erdosproblems.com, הבהיר ש"פתוחה" באתר שלו פירושה רק שהוא לא מכיר מאמר שפותר אותה, ושהמודל **מצא מאמרים קיימים** שכבר פתרו את הבעיות. הציוצים נמחקו, ו-Demis Hassabis כינה את האירוע "מביך". **הלקח: המודל היה מצוין בחיפוש ספרות, וזה ערך אמיתי, אבל זה לא גילוי מתמטי.**

**ינואר 2026 ואילך:** מגיעים פתרונות חדשים באמת. לבעיה **#728** הגיעו GPT-5.2 Pro ו-Aristotle עם הוכחה פורמלית ב-Lean (6 בינואר 2026, arXiv:2601.07421). זו נחשבת בדרך כלל לבעיית ארדש הראשונה שנפתרה באופן אוטונומי בעיקרו. אחריה באו בעיות נוספות (למשל #397) ([לא אומת]: ספירות של "15 בעיות" ממקורות משניים).

**ויקי של Tao** ([teorth/erdosproblems wiki](https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems), עודכן עד 30 ביוני 2026, ומאז לא מתעדכן): בקטגוריה "AI standalone" יש כ-61 רשומות. רק כ-19 מהן פתרון מלא, כ-10 **שגויות**, וכ-9 לא אומתו. עוד כ-25 רשומות הן פתרונות שהתברר בדיעבד **שכבר היו בספרות**. ההסתייגויות שבוויקי:
- "This page is not a benchmark."
- "Keep selection bias in mind."
- "**Absence of past progress may reflect obscurity rather than difficulty.**"
- פתרון לבעיית ארדש אינו בהכרח מאמר שראוי לפרסום.

**הלקחים:** (א) בדיקת ספרות קודמת לכל דבר אחר. (ב) הבעיות ש-AI פותר הן בדרך כלל "הזנב הארוך" של בעיות שאיש לא ניסה ברצינות, ולא הבעיות הקשות. (ג) Lean הפך את הוויכוח מ"האם זה נכון?" לשאלה "האם זה חדש וחשוב?".

---

## 5. בנצ'מרקים: FrontierMath, HLE, זיהום ו-hype

- **FrontierMath** (Epoch AI, נובמבר 2024): בעיות מחקר עם תשובה מספרית שאפשר לבדוק אוטומטית. בהתחלה מודלים פתרו פחות מ-2%. בדצמבר 2024 OpenAI הודיעה שמודל o3 הגיע לכ-25%. **מחלוקת (ינואר 2025):** התברר ש-OpenAI מימנה את הבנצ'מרק ויש לה גישה לחלק מהבעיות, ו-Epoch לא הצליחו לשחזר באופן עצמאי את התוצאה המקורית. ב-2026 נוסף Tier 4. ביוני 2026 שוחררה גרסה v2 מתוקנת: 12 בעיות תוקנו ו-7 הוסרו, כלומר **גם בבנצ'מרק מוקפד היו שגיאות**. ציונים עדכניים מתפרסמים בדיווחים סותרים ([לא אומת]: נתונים על Tier 4 מעל 80%).
- **Humanity's Last Exam** (CAIS ו-Scale AI, ינואר 2025): כ-2,500 שאלות. ביקורות מאוחרות מצאו שיעור משמעותי של תשובות "נכונות" שגויות או שנויות במחלוקת, במיוחד בכימיה ובביולוגיה ([לא אומת]: הנתון המדויק).
- **זיהום (contamination):** miniF2F ובעיות אולימפיאדה ישנות דלפו לנתוני האימון. לכן IMO חי, First Proof ובעיות לא מפורסמות הן מדד אמין יותר.
- **Selection bias:** מכריזים על ההצלחות, ועל אלפי הניסיונות הכושלים לא מדווחים.

---

## 6. פיזיקה תיאורטית

| תחום | דוגמאות | הערכה |
|---|---|---|
| **רגרסיה סימבולית** | AI Feynman (Udrescu & Tegmark, Science Advances 2020); PySR (Cranmer, 2023) | שחזור נוסחאות מנתונים. עובד היטב על "נוסחאות ספר", ופחות על פיזיקה חדשה באמת. |
| **אמפליטודות ו-bootstrap** | transformers שמנבאים מקדמים באמפליטודות של N=4 SYM (Dixon, Charton ואחרים, 2024–2025); ML לחיפוש במרחב ה-bootstrap של CFT | מבטיח, כי יש מבנה אלגברי עשיר שאפשר לבדוק אותו בחישוב. |
| **אמפליטודות גלואונים 2026** | "Single-minus gluon tree amplitudes are nonzero" (Guevara, Lupsasca, Skinner, Strominger, Weil, פברואר 2026): GPT-5.2 Pro הציע נוסחה כללית מתוך מקרים שחושבו בידי בני אדם, וגרסה פנימית שלו הפיקה הוכחה שבני אדם וידאו | תרומה אמיתית אבל צרה. שניים מהמחברים מ-OpenAI. Witten אולי רמז על האפשרות ב-2003. **גם כאן ה-verifier (בדיקה אנליטית) הוא שהפך את זה לתוצאה.** |
| **String landscape** | He; Ruehle; Carifio, Halverson, Krioukov, Nelson (2017 ואילך): ML על Calabi–Yau ומספרי Hodge | כלי סיווג וחיפוש שימושי, ולא פריצת דרך בשאלות היסוד. |
| **Lattice QCD** | normalizing flows לדגימה (Albergo, Kanwar, Shanahan, 2019 ואילך) | השפעה מעשית אמיתית על עלויות חישוב, עם ערבויות סטטיסטיות מדויקות (המדגם מתוקן). |

**לקח כללי לפיזיקה:** ההצלחות נמצאות היכן שיש **בדיקה עצמאית**: חישוב אנליטי, סימטריות, גבולות ידועים או סימולציה. "תיאוריה חדשה של הכול" מ-LLM היא רעש.

---

## 7. מסקנות

1. **אימות גובר על יצירה (Verification beats generation).** כל תוצר של המעבדה מסתיים ב-Lean (בלי `sorry` ועם `#print axioms` נקי) או בחישוב שאפשר לשחזר (קוד, seed, תוצאה עם hash). אם אין verifier, אין תוצאה.
2. **הניצחון הזול ביותר הוא חיפוש ספרות.** לפני שתוקפים בעיה "פתוחה", מריצים חיפוש ספרות שיטתי (LLM, arXiv, MathSciNet, zbMATH, OEIS), ומתעדים אותו. חלק ניכר מבעיות ארדש ש"נפתרו" ב-2025 כבר היו פתורות.
3. **בוחרים בעיות עם ציון מספרי.** בעיות בנייה עם objective (חסמים, צפיפויות, אריזות, מספרי Ramsey קטנים, כפל מטריצות) מתאימות ביותר לצוות קטן עם חיפוש אבולוציוני ו-verifier, בסגנון FunSearch ו-AlphaEvolve.
4. **המעריך הוא קוד קריטי.** מערכות אבולוציוניות מנצלות באגים במעריך. כותבים לו טסטים, משתמשים בחשבון מדויק (rationals או intervals) ולא ב-floats, ובודקים כל שיפור במעריך נוסף ובלתי תלוי.
5. **הוכחות בשפה טבעית שמגיעות מ-LLM אינן אמינות בלי בדיקה פורמלית.** משתמשים ב-LLM ככותב סקיצות, ולאחר מכן מפרמלים (ידנית או עם מפרמל אוטומטי).
6. **בודקים את הטענה, לא רק את ההוכחה.** טענה שפורמלה לא נכון היא הכשל השקט המסוכן ביותר. כל statement ב-Lean עובר review אנושי ומול המקור, ורצוי השוואה אוטומטית (comparator) ל-statement קיים ב-mathlib.
7. **מכוונים לזנב הארוך.** הבעיות ש-AI פותר הן בדרך כלל מוזנחות ולא קשות. בוחרים במודע בעיות שאיש לא ניסה ברצינות, ולא מתיימרים להכריע את השערת רימן.
8. **Blueprint לפני קוד.** בכל פורמליזציה גדולה (LTE, PFR, FLT, Strong PNT) הייתה מפה של למות ותלויות. סוכנים מצליחים כשהעבודה מפורקת ליחידות קטנות שאפשר לבדוק כל אחת בנפרד.
9. **לא בונים מה שקיים.** משתמשים ב-mathlib, ב-LeanDojo, במוכיחים פתוחים (DeepSeek-Prover, Goedel, Kimina) ובשירותי פורמליזציה. היתרון של צוות קטן הוא בבחירת הבעיות ובמעריכים, ולא באימון מודלים מאפס.
10. **לולאת סוכן עם משוב מהקומפיילר.** הצנרת שעובדת ב-2025–2026: LLM כותב, Lean מחזיר שגיאות, LLM מתקן, וחוזר חלילה, עם retrieval של למות מ-mathlib. משקיעים בתשתית הזו: build מהיר, cache וגרסת mathlib נעולה.
11. **מתעדים ומפרסמים תוצאות שליליות ו-datasets.** ניסיונות כושלים, statements מפורמלים וטבלאות של חסמים הם תרומה. ויקי ארדש של Tao מראה שתיעוד שקוף של כישלונות שווה יותר מהכרזות.
12. **חלוקה מפורשת של קרדיט ותפקידים.** בכל תוצאה מתעדים מה עשה ה-AI (חיפוש, סקיצה, פורמליזציה, חישוב) ומה עשו בני אדם, לפי הקטגוריות של ויקי ארדש.
13. **מודדים על בעיות שלא דלפו.** לא מצטטים ציוני miniF2F כראיה ליכולת. מעריכים על בעיות חדשות או פרטיות (בסגנון First Proof) ומדווחים על כל הניסיונות, לא רק על ה-best-of-N.
14. **AI כמיקרוסקופ להשערות.** בסגנון Davies et al. ו-Ramanujan Machine: מייצרים נתונים, מחפשים דפוסים ומנסחים השערות, ואז מנסים להוכיח או להפריך. השערה מנוסחת היטב היא תוצר לגיטימי, כל עוד מסומנת כהשערה.
15. **בפיזיקה בוחרים תתי-בעיות עם בדיקה עצמאית:** אמפליטודות עם גבולות ידועים, bootstrap מספרי, בעיות סימולציה. לא "תיאוריות חדשות" שאי אפשר לבדוק.
16. **שתי עיניים אנושיות מומחיות לפני כל הכרזה פומבית.** גם אחרי Lean, מומחה בתחום צריך לאשר שהתוצאה חדשה ושיש לה משמעות.
17. **מתכננים תקציב חישוב.** AlphaProof דרש ימים של חישוב לבעיה, ו-FLT של Anthropic דרש כ-6 מיליארד טוקנים. מעדיפים בעיות שבהן כל ניסיון זול ובדיקתו מהירה.

---

## 8. מה לא לעשות (Anti-patterns)

- **לא להכריז על הוכחה של רימן, P≠NP, Navier–Stokes וכדומה.** כל טענה כזו מ-LLM היא כמעט בוודאות שגויה, וגם תפגע באמינות המעבדה.
- **לא לפרסם "פתרנו בעיה פתוחה" לפני חיפוש ספרות ובדיקה פורמלית.** פרשת אוקטובר 2025 היא המקרה שממנו לומדים.
- **לא לסמוך על הוכחה בשפה טבעית רק משום שהיא "נראית טוב".** מודלים כותבים הוכחות שגויות ומשכנעות.
- **לא להשתמש ב-`sorry`, ב-`axiom` או ב-`native_decide` בלי סימון מפורש.** כל אלה נבדקים ב-CI.
- **לא לפרמל טענה חלשה או שגויה ולהציג אותה כמשפט המקורי.**
- **לא לצטט ציוני בנצ'מרק שמגיעים מהיצרן** בלי לציין שהם לא אומתו ושיש חשש לזיהום.
- **לא לבחור בעיה בלי קריטריון הצלחה מוגדר** (ציון, statement פורמלי, או חישוב).
- **לא לייצר "מאמרי AI" בכמויות.** פתרון שולי לבעיה מוזנחת אינו מאמר. מפרסמים אותו כרשומה ב-dataset או כפתק קצר.
- **לא להסתיר את תפקיד ה-AI, וגם לא לנפח אותו.**
- **לא לאמן מודלים מאפס** כשמודל פתוח ומוכן כבר קיים.

---

## 9. מקורות

**פורמליזציה**
- Liquid Tensor Experiment: https://leanprover-community.github.io/blog/posts/lte-final/
- PFR formalization (Tao blog, 2023): https://terrytao.wordpress.com/2023/12/05/a-slightly-longer-lean-4-proof-tour/ ; https://teorth.github.io/pfr/
- Equational Theories Project: https://teorth.github.io/equational_theories/
- FLT project (Imperial): https://imperialcollegelondon.github.io/FLT/
- Anthropic, "Formalizing Fermat's Last Theorem" (2026-09-04): https://www.anthropic.com/research/formalizing-fermats-last-theorem
- Buzzard, "FLT: Anthropic has beaten me to it" (2026-09-04): https://xenaproject.wordpress.com/2026/09/04/flt-anthropic-has-beaten-me-to-it/ (לא נקרא ישירות)
- Math Inc. Gauss / Strong PNT: https://math-inc.github.io/strongpnt ; דיון ב-Zulip: https://leanprover-community.github.io/archive/stream/219941-Machine-Learning-for-Theorem-Proving/topic/Math.2C.20Inc.2C.20and.20Gauss.20discussion.html

**מוכיחי משפטים**
- GPT-f: https://arxiv.org/abs/2009.03393
- miniF2F: https://arxiv.org/abs/2109.00110
- HTPS: https://arxiv.org/abs/2205.11491
- LeanDojo: https://arxiv.org/abs/2306.15626
- PutnamBench: https://arxiv.org/abs/2407.11214
- DeepSeek-Prover V1/V1.5/V2: https://arxiv.org/abs/2405.14333 , https://arxiv.org/abs/2408.08152 , https://arxiv.org/abs/2504.21801
- Goedel-Prover: https://arxiv.org/abs/2502.07640
- Kimina-Prover: https://arxiv.org/abs/2504.11354
- Seed-Prover: https://arxiv.org/abs/2507.23726 ; https://seed.bytedance.com/en/blog/bytedance-seed-prover-achieves-silver-medal-score-in-imo-2025
- AlphaGeometry (Nature 2024): https://www.nature.com/articles/s41586-023-06747-5
- AlphaProof, IMO 2024: https://deepmind.google/discover/blog/ai-solves-imo-problems-at-silver-medal-level/
- AlphaProof (Nature, 2025-11-12): https://www.nature.com/articles/s41586-025-09833-y
- Aristotle: https://arxiv.org/abs/2510.01346
- Gemini Deep Think, IMO 2025: https://deepmind.google/discover/blog/advanced-version-of-gemini-with-deep-think-officially-achieves-gold-medal-standard-at-the-international-mathematical-olympiad/
- First Proof: https://1stproof.org/ ; https://arxiv.org/abs/2602.05192 ; https://ethz.ch/staffnet/en/news-and-events/internal-news/archive/2026/07/eth-team-wins-first-proof-challenge-for-ai-assisted-mathematical-research.html

**חיפוש וגילוי**
- Wagner 2021: https://arxiv.org/abs/2104.14516
- Ramanujan Machine: https://www.nature.com/articles/s41586-021-03229-4
- Davies et al. 2021: https://www.nature.com/articles/s41586-021-04086-x
- FunSearch: https://www.nature.com/articles/s41586-023-06924-6
- PatternBoost: https://arxiv.org/abs/2411.00566
- AlphaEvolve: https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
- Georgiev, Gómez-Serrano, Tao, Wagner (2025): https://arxiv.org/abs/2511.02864

**ארדש**
- AI contributions wiki: https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems
- Erdős #728 writeup: https://arxiv.org/abs/2601.07421
- סיקור פרשת אוקטובר 2025: https://www.eweek.com/news/openai-math-hype/

**בנצ'מרקים**
- FrontierMath: https://epoch.ai/frontiermath
- מחלוקת המימון: https://techcrunch.com/2025/01/19/ai-benchmarking-organization-criticized-for-waiting-to-disclose-funding-from-openai
- Humanity's Last Exam: https://lastexam.ai/

**פיזיקה**
- AI Feynman: https://www.science.org/doi/10.1126/sciadv.aay2631
- Single-minus gluon amplitudes (2026), סיקור: https://phys.org/news/2026-02-chatbot-author-ai-stalled-gluon.html ; ניתוח ביקורתי: https://huggingface.co/blog/dlouapre/gpt-single-minus-gluons
- Normalizing flows for lattice field theory: https://arxiv.org/abs/1904.12072
- ML ב-string landscape: https://arxiv.org/abs/1706.02714 (He) ; https://arxiv.org/abs/1707.00655 (Carifio et al.)
