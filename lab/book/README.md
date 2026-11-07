# ספר התיעוד — "המעבדה"

ספר התיעוד של ESH27 Lab מתעד את הפרויקט ואת הרקע שלו, והוא מקור התוכן לכל מה שנפרסם (S27 News, פוסטים וסרטונים). בסוף כל פרק יש סעיף **"רעיונות לתוכן"**.

| קובץ | פרק |
|---|---|
| `chapters/00-preface.md` | הקדמה |
| `chapters/01-what-is-a-proof.md` | מהי הוכחה? |
| `chapters/02-great-problems.md` | הבעיות הגדולות |
| `chapters/03-machines-and-proofs.md` | מכונות והוכחות |
| `chapters/04-ai-and-math.md` | AI ומתמטיקה 2019–2026 |
| `chapters/05-lean-hands-on.md` | Lean 4 בידיים |
| `chapters/06-architecture.md` | ארכיטקטורת המעבדה |
| `chapters/06a-five-foundations.md` | חמשת היסודות |
| `chapters/07-goal-bank.md` | בנק המטרות |
| `chapters/08-toolbox.md` | ארגז הכלים |
| `chapters/09-creative-proofs.md` | דפוסי הוכחה יצירתיים |
| `chapters/10-theoretical-physics.md` | פיזיקה תיאורטית |
| `chapters/11-wisdom-bridges.md` | גשרי חוכמה |
| `chapters/12-ethics-and-publishing.md` | יושרה, אתיקה ופרסום |
| `chapters/13-operations-log.md` | יומן מבצעים (חי) |
| `chapters/98-glossary.md` | מילון מונחים |
| `chapters/99-bibliography.md` | ביבליוגרפיה |

## בנייה

```bash
./build.sh   # -> dist/book.html, dist/book.epub, dist/book.pdf
```

הבנייה דורשת pandoc, וליצירת ה-PDF גם Node עם Playwright. כללי הכתיבה נמצאים ב-`STYLE.md`.
