# ארגז הכלים של ESH27 Lab

> עודכן: 2026-11-04 · הקטלוג המלא (140 כלים, 19 קטגוריות): [`data/tools.csv`](../data/tools.csv) · סקריפט התקנה: [`scripts/setup.sh`](../scripts/setup.sh)

המשימה של המעבדה: לתקוף בעיות פתוחות במתמטיקה ובפיזיקה תיאורטית בעזרת AI + Lean 4.
העיקרון המנחה: **כל טענה עוברת דרך מכונה שבודקת** — Lean לטענות מתמטיות, ‏DRAT/LRAT לתוצאות SAT, אריתמטיקת כדורים (Arb) לנומריקה.

## מבנה הקטלוג

| עמודה | משמעות |
|---|---|
| `id` | ‏T001…T140 |
| `category` | אחת מ‑19 הקטגוריות (proof-assistant, lean-library, ai-prover, llm-api, search/evolution, SAT/SMT, CAS, numerics, combinatorics, number-theory, geometry/topology, physics, literature-search, datasets/benchmarks, notation/translation, collaboration/publishing, infra/compute, visualization, hebrew/jewish-texts) |
| `maturity` | ‏1 = ניסיוני/לא זמין · 3 = שמיש עם חספוסים · 5 = סטנדרט תעשייתי |
| `license_or_cost` | רישיון או מודל תמחור (לבדוק מחדש לפני שימוש מסחרי) |

הערות חשובות:
- **AlphaProof** אינו זמין לציבור — רשום לצורך הקשר בלבד.
- **FrontierMath** ברובו פרטי — אי אפשר להריץ עליו בעצמנו.
- **Aristotle (Harmonic)** — שרת ה‑API עשוי לרוץ על גרסת Lean ישנה מזו שלנו, והשאילתות נשמרות אצל הספק. לא לשלוח חומר רגיש.

## ה‑Starter Stack — 15 הכלים שמתקינים ראשונים

| # | כלי | למה ראשון |
|---|---|---|
| 1 | **Lean 4 + elan** | שפת האימות המרכזית; elan מצמיד גרסת toolchain לכל פרויקט. |
| 2 | **Lake + mathlib4** | בלי mathlib אין מתמטיקה; `lake exe cache get` חוסך שעות קומפילציה. |
| 3 | **Lean REPL / lean-lsp-mcp** | הממשק שדרכו סוכני AI רואים goals ובודקים הוכחות. |
| 4 | **LeanSearch + Loogle** (web) | מציאת הלמה הנכונה — שפה טבעית (LeanSearch) או לפי צורת טיפוס (Loogle). |
| 5 | **Claude API + Claude Agent SDK** | מנוע ההיגיון והתזמור של לולאות המחקר (הוכחה, ספרות, ניסויים). |
| 6 | **MCP** | פרוטוקול אחיד לחשיפת Lean, ‏OEIS, ‏arXiv ופותרי SAT כ"כלים" לסוכנים. |
| 7 | **Python venv** (‏numpy, scipy, pandas, matplotlib, jupyter) | שכבת הדבק לכל הניסויים והלוגים. |
| 8 | **SymPy** | חישוב סימבולי קל בתוך צינורות הסוכנים. |
| 9 | **mpmath** | דיוק שרירותי לזיהוי קבועים וניסויים נומריים. |
| 10 | **NetworkX** | אב‑טיפוס מהיר לבעיות גרפים וקומבינטוריקה. |
| 11 | **PySAT** | קידודי SAT (כולל cardinality) מפייתון, מעל פותרים רבים. |
| 12 | **Z3** | SMT לבדיקות אריתמטיות וחסמים קטנים. |
| 13 | **Kissat + DRAT-trim** (אופציונלי) | פותר SAT מוביל + בודק תעודות UNSAT — כדי ש"אין פתרון" יהיה מוכח. |
| 14 | **OEIS + arXiv API** (web) | זיהוי סדרות שיוצאות מניסויים; סריקה יומית של ספרות חדשה. |
| 15 | **GitHub Actions + lean-action** | CI שבודק כל הוכחה בכל PR — אין "עובד אצלי". |

אופציונלי בשלב ראשון: **PySR** (רגרסיה סימבולית — מושך Julia, כבד), **OpenEvolve/ShinkaEvolve** (אבולוציית תוכניות בסגנון AlphaEvolve), **SageMath / PARI/GP** (כש‑SymPy לא מספיק), **Sefaria API** (טקסטים יהודיים, לפרויקטי gematria/טקסט).

## תוכנית סקריפט ההתקנה (`scripts/setup.sh`)

הסקריפט **אידמפוטנטי**: כל שלב בודק אם הכלי כבר קיים ומדלג. מיועד ל‑Ubuntu 22.04/24.04.

| שלב | מה קורה | ברירת מחדל |
|---|---|---|
| 1 | חבילות apt: ‏git, curl, build-essential, python3-venv | פועל (רק מה שחסר) |
| 2 | התקנת elan + toolchain ‏`stable` של Lean 4 | פועל |
| 3 | יצירת venv ב‑`lab/.venv` | פועל |
| 4 | ‏pip: sympy, numpy, scipy, networkx, python-sat, z3-solver, mpmath, pandas, openpyxl, matplotlib, jupyter, requests, anthropic, claude-agent-sdk + בדיקת import | פועל |
| 5 | PySR | `WITH_PYSR=1` |
| 6 | בניית Kissat ו‑DRAT-trim מהמקור ל‑`~/.local/esh27-tools`, קישור ל‑`~/.local/bin` | `WITH_KISSAT=1` |
| 7 | ‏`lake exe cache get && lake build` בפרויקט `lab/lean` (אם קיים lakefile) | `WITH_MATHLIB=1` |

```bash
bash lab/scripts/setup.sh                              # ליבה
WITH_PYSR=1 WITH_KISSAT=1 bash lab/scripts/setup.sh    # הכל
source lab/.venv/bin/activate
export ANTHROPIC_API_KEY=...                           # לא לשמור במאגר!
```

### צעדים הבאים (לא בסקריפט)
- **Docker image** של המעבדה (Lean + mathlib cache + venv) לשימוש ב‑CI וב‑Modal/RunPod.
- הרצת מוכיחים פתוחים (DeepSeek-Prover-V2, Goedel-Prover-V2, Kimina-Prover) דרך **vLLM** על GPU ענני — רק כשיש תקציב GPU.
- שרתי MCP פנימיים: OEIS, LMFDB, arXiv, פותרי SAT.
- רישיונות אקדמיים: Gurobi, MOSEK (חינם לאקדמיה); Mathematica/Magma רק אם פרויקט ספציפי דורש.

## קטגוריות — ספירה

| קטגוריה | כלים |
|---|---|
| lean-library | 14 |
| CAS | 11 |
| physics | 11 |
| numerics | 10 |
| llm-api | 9 |
| literature-search | 9 |
| proof-assistant | 8 |
| SAT/SMT | 8 |
| collaboration/publishing | 8 |
| infra/compute | 8 |
| hebrew/jewish-texts | 8 |
| ai-prover | 6 |
| search/evolution | 6 |
| combinatorics | 5 |
| geometry/topology | 5 |
| datasets/benchmarks | 5 |
| notation/translation | 4 |
| visualization | 3 |
| number-theory | 2 |
| **סה"כ** | **140** |
