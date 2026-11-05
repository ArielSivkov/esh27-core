# G050: מספרי Schur ו-van der Waerden קטנים, צינור SAT→Lean (דו"ח, 2026-11-05)

**שורה תחתונה:** ב-Lean 4.24.0 הוכחו, בבדיקת kernel בלבד וללא `native_decide`, ש-S(1)=1, S(2)=4, S(3)=13 ו-W(2,3)=9, וגם החסמים התחתונים S(4)≥44, W(3,3)>26 ו-W(2,4)>34.
המשפטים W(2,4)=35 ו-W(3,3)=27 הוכחו ב-Lean דרך תעודת LRAT של CaDiCaL שנבדקה ב-checker ה-LRAT המאומת של Lean core. הבדיקה רצה עם `native_decide`, ולכן התוצאות האלה חלשות יותר מבדיקת kernel בלבד.
החסם העליון של S(4)=44 **לא** הוכח ב-Lean. הוא אומת רק ברמת ה-CNF, בעזרת drat-trim ו-lrat-check.

## 1. סביבה
- Lean `leanprover/lean4:v4.24.0` הותקן דרך elan. השרת release.lean-lang.org חסום ב-proxy (403), ולכן ה-tarball ירד מ-GitHub releases והוקשר עם `elan toolchain link`.
- Mathlib: גם cache של mathlib חסום (`lakecache.blob.core.windows.net` מחזיר 403), ובנייה מהמקור לוקחת שעות. לכן G050 **לא תלוי ב-Mathlib**. הוא package עצמאי ב-`lab/lean/G050/` (`srcDir = ".."`), שבונה רק את `EshLab/Targets/G050*.lean`. ב-lakefile הראשי הוצמד mathlib ל-`rev = "v4.24.0"` במקום `master`. **`lake build` של כל פרויקט EshLab לא הורץ**, כי Basic, Collatz ו-Goldbach דורשים Mathlib.
- SAT: CaDiCaL 3.0.1 (commit c607304) ו-drat-trim/lrat-check (commit 2e3b2dc). שניהם נבנים מהמקור על ידי `setup_tools.sh`. python-sat משמש רק לחיפוש עדים.

## 2. הניסוחים: מה בדיוק נטען (failure mode #1)
הקובץ `Defs.lean`. צביעה היא `c : Nat → Fin k`, ורק הערכים `c 1..c n` רלוונטיים.
- `SchurFree k n c`: אין `x, y ≥ 1` עם `x+y ≤ n` כך ש-`c x = c (x+y)` ו-`c y = c (x+y)`. המקרה `x = y` כלול, כלומר זה מספר Schur הקלאסי (OEIS A030126).
- `IsSchurNumber k s`: יש צביעה טובה של {1..s}, ואין צביעה טובה של {1..s+1}. הלמה `IsSchurNumber.iff` מוכיחה שקיימת צביעה טובה של {1..n} ⇔ n ≤ s, ולכן s הוא בדיוק **המקסימום**. הלמה `IsSchurNumber.unique` מוכיחה שהערך יחיד.
- `APFree k L n c`: אין `a ≥ 1` ו-`d ≥ 1` עם `a+(L-1)d ≤ n` כך שכל האיברים `c(a+i·d)`, ל-`i < L`, שווים.
- `IsVdWNumber k L w`: יש צביעה טובה של {1..w-1}, ואין צביעה טובה של {1..w}. הלמה `IsVdWNumber.iff` מוכיחה שקיימת צביעה טובה ⇔ n < w, כלומר w הוא **המינימום**. סדר הפרמטרים הוא W(k colours, L length), ולכן W(2,3)=9 נכתב `IsVdWNumber 2 3 9`.
- `Lower.lean` כולל גם דוגמאות שליליות שבודקות שההגדרות דוחות צביעות רעות. בין היתר, ההרחבות של עד S(2) ל-5, בכל אחד משני הצבעים, נכשלות.
- **ה-targets עוד לא נבדקו על ידי אדם** (`reviewed_by` ריק). לפי הנוהל, נדרשת סקירה אנושית של `Defs.lean`.

## 3. מה הוכח ובאיזו רמת אמון
| משפט ב-Lean | מתמטיקה | שיטה | axioms |
|---|---|---|---|
| `schur_one`, `schur_two`, `schur_three` | S(1)=1, S(2)=4, S(3)=13 | עד מפורש + חיפוש ממצה מאומת, `decide +kernel` | propext, Classical.choice, Quot.sound |
| `vdw_two_three` | W(2,3)=9 | כנ"ל | כנ"ל |
| `schur4_lower`, `vdw3_3_lower`, `vdw2_4_lower` | S(4)≥44, W(3,3)>26, W(2,4)>34 | עד מ-CaDiCaL, נבדק ב-`decide +kernel` | כנ"ל |
| `ViaLRAT.vdw_two_four`, `ViaLRAT.vdw_three_three` | W(2,4)=35, W(3,3)=27 | תחתון ב-kernel. עליון: LRAT + `LRAT.check_sound` + `native_decide` | + `Lean.ofReduceBool`, `Lean.trustCompiler` |
| `ViaLRAT.schur2_upper`, `schur3_upper`, `vdw2_3_upper` | הוכחה שנייה ובלתי תלויה לחסמים העליונים | LRAT + `native_decide` | כנ"ל |

**שני מסלולים לחסם עליון:**
1. **חיפוש ממצה מאומת (`Search.lean`), בבדיקת kernel בלבד.** `layer ok k n` מונה את כל רשימות הצבעים שעוברות בדיקה מקומית, ללא שבירת סימטריה. השקילות בין הבדיקה המקומית לבין ההגדרה המתמטית מוכחת (`schurFree_iff`, `apFree_iff`), ונאותות החיפוש מוכחת ב-`pre_mem_layer`. ב-S(3) יש 1,953 צמתים, וה-kernel בודק אותם בכ-31 שניות. ב-W(2,4) יש כ-20 אלף צמתים, וה-kernel **נגמר לו הזיכרון**: יותר מ-14GB, exit 137, אחרי כ-4 דקות. ב-W(3,3) יש כ-675 אלף צמתים, וזה לא נוסה.
2. **SAT→Lean (`LRAT.lean`).** ה-CNF נבנה **ב-Lean** (`schurCNF`, `vdwCNF`) באותו סדר clauses כמו ב-`encode.py`. מוכח ב-Lean שכל צביעה טובה מספקת אותו (`schurCNF_sat`, `vdwCNF_sat`), ולכן ה-encoder של Python אינו בבסיס האמון. הוכחת ה-LRAT הגולמית של CaDiCaL מוטמעת כ-`String` (`Certs/*.lean`, נוצר על ידי `lrat_to_lean.py`). הפענוח נעשה ב-parser של Lean core, והבדיקה ב-`Std.Tactic.BVDecide.LRAT.check`, שזה ה-checker ש-`bv_decide` משתמש בו ושנאותותו מוכחת ב-`check_sound`. ניסינו גם `decide +kernel` על ה-checker עצמו, אבל ה-kernel נתקע: הקוד מבוסס `Array` ו-well-founded recursion, ולא מצטמצם. לכן הצעד הזה נעשה ב-`native_decide`, שסומך על הקומפיילר. זו בדיוק רמת האמון של `bv_decide`.

**הצעה ל-ledger:** שורות ה-kernel נרשמו כ-L3, עם תעודת lean ו-verified. שורות ה-`native_decide` נרשמו כ-**L1** עם `verified: false`, עד שה-verifier יחליט אם `Lean.ofReduceBool` מקובל כ-L3.

## 4. צד ה-SAT (`results.json`), ללא שבירת סימטריה
| מופע (UNSAT) | clauses | זמן פתרון | DRAT | בדיקת drat-trim | LRAT | lrat-check |
|---|---|---|---|---|---|---|
| Schur k=2, n=5 | 17 | 0.003s | 48B | ✔ | 191B | ✔ |
| Schur k=3, n=14 | 161 | 0.005s | 6.7KB | ✔ 0.07s | 19.5KB | ✔ |
| Schur k=4, n=45 | 2069 | **190s** | **361MB** | ✔ **415s** | **606MB** | ✔ 13s |
| vdW 2,3, n=9 | 41 | 0.03s | 211B | ✔ | 692B | ✔ |
| vdW 3,3, n=27 | 534 | 0.15s | 451KB | ✔ 0.6s | 832KB | ✔ |
| vdW 2,4, n=35 | 409 | 0.01s | 22KB | ✔ | 61KB | ✔ |

העדים לחסמים התחתונים נמצאו בפחות מ-0.2 שניות, ונבדקו גם בבודק מדויק ב-Python וגם ב-Lean.

**זמנים ב-Lean:** בנייה נקייה של `lab/lean/G050` לוקחת 43 שניות (4 ליבות). רובה, 32 שניות, ב-`Upper.lean`, בגלל החיפוש של S(3). בדיקות ה-LRAT ב-`native_decide` לוקחות פחות משנייה כל אחת, כולל W(3,3). הפלט המלא נמצא ב-`lake_build.log`, יחד עם הפלט של `#print axioms`.

## 5. מה לא נעשה, ומה החסם
- **S(4)=44, חסם עליון ב-Lean:** ההוכחה בלי שבירת סימטריה גדולה מדי. ה-DRAT שוקל 361MB, ה-LRAT שוקל 606MB, ואחרי trim ב-drat-trim (7 דקות) עדיין נשארו 520MB, עם 2.47M lemmas ו-59M צעדי רזולוציה. אי אפשר להטמיע את זה כ-String בקובץ מקור.
- **W(2,4) ו-W(3,3) בבדיקת kernel בלבד:** החיפוש הממצה ב-kernel נכשל בגלל זיכרון (W(2,4)), ובדיקת LRAT ב-kernel נתקעת.
- **`lake build` של EshLab המלא** חסום עד שתהיה גישה ל-cache של Mathlib, או עד שתושלם בנייה מהמקור.

## 6. הצעדים הבאים
1. **S(4):**
   - שבירת סימטריית צבעים שמוכחת ב-Lean: פרמוטציה של הצבעים שומרת על `SchurFree`. לקבע c(1)=0, וצבע חדש מופיע בסדר עולה. זה מקטין את ההוכחה בערך פי 4! = 24.
   - cube-and-conquer, כך שכל cube מקבל תעודה קטנה.
   - elaborator שקורא קובץ LRAT בזמן build במקום הטמעה בקוד, או פורמט בינארי.
   - יעד ריאלי: הוכחה באורך עשרות MB, ובדיקה ב-`native_decide` של כמה דקות.
2. **בדיקת LRAT ב-kernel בלבד:** לכתוב checker פשוט מבוסס `List` עם רקורסיה מבנית, שמתאים ל-kernel, ולהוכיח את נאותותו. או לבדוק את גרסאות Lean החדשות יותר, שבהן `Nat`/`Array` עוברים reduction טוב יותר. המטרה היא להוריד את `ofReduceBool` מ-W(2,4) ומ-W(3,3).
3. **סקירה אנושית** של `Defs.lean`, ואז קידום ה-targets.
4. **בהמשך:** W(2,5)=178 ו-R(3,3,3)=17, כפי שמוצע ב-goal-bank.
