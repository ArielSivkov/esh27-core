---
chapter: 99
title: "ביבליוגרפיה"
title_en: "Bibliography"
status: draft
---

# נספח ב: ביבליוגרפיה

הנספח הזה מאחד את המקורות שמופיעים במסמכים שבתיקייה `docs/` (`ai-math-lessons.md`, `architecture.md`, `creative-proofs.md`, `goal-bank.md`, `theoretical-physics.md`, `tools.md`, `wisdom-bridges.md`) ובקובצי הנתונים שהם מפנים אליהם (`data/creative_proofs.csv`, `data/goals.csv`, `data/tools.csv`, `data/wisdom_projects.csv`). כל מקור מופיע פעם אחת, תחת הנושא המתאים ביותר, גם אם כמה מסמכים מפנים אליו.

מקורות שלא נקראו ישירות, או שפרטיהם לא אומתו, מסומנים [לא אומת], כמו במסמכי המקור. מקור בלי URL הוא ספר או מאמר שהמסמכים מצטטים בלי קישור; כשמופיע מזהה arXiv, הקישור נבנה ממנו. הספר מפנה לנספח מתוך הערות השוליים בפרקים.

## 1. פורמליזציה ועוזרי הוכחות

### פרויקטים גדולים

- **Liquid Tensor Experiment** (Scholze; Commelin ושותפים, 2020–2022). https://leanprover-community.github.io/blog/posts/lte-final/ ; https://github.com/leanprover-community/lean-liquid
- **PFR** (Gowers, Green, Manners, Tao, 2023), ההוכחה: https://arxiv.org/abs/2311.05762 ; הפורמליזציה: https://teorth.github.io/pfr/ ; Tao, "A slightly longer Lean 4 proof tour": https://terrytao.wordpress.com/2023/12/05/a-slightly-longer-lean-4-proof-tour/
- **Equational Theories Project** (Tao ושותפים, 2024–2025). https://teorth.github.io/equational_theories/ ; https://github.com/teorth/equational_theories
- **פרויקט FLT** (Imperial College, Buzzard). https://imperialcollegelondon.github.io/FLT/
- Anthropic, "Formalizing Fermat's Last Theorem" (2026-09-04). https://www.anthropic.com/research/formalizing-fermats-last-theorem
- K. Buzzard, "FLT: Anthropic has beaten me to it" (2026-09-04). https://xenaproject.wordpress.com/2026/09/04/flt-anthropic-has-beaten-me-to-it/ [לא אומת: לא נקרא ישירות]
- **Math Inc. Gauss, Strong PNT** (2025). https://math-inc.github.io/strongpnt ; דיון ב-Zulip: https://leanprover-community.github.io/archive/stream/219941-Machine-Learning-for-Theorem-Proving/topic/Math.2C.20Inc.2C.20and.20Gauss.20discussion.html
- **mathlib stats**. https://leanprover-community.github.io/mathlib_stats.html

### פורמליזציה של הוכחות ממוחשבות

- G. Gonthier, "Formal Proof—The Four-Color Theorem", Notices AMS 55 (2008).
- T. Hales et al., "A formal proof of the Kepler conjecture" (Flyspeck), Forum of Math, Pi 5 (2017).
- B. Subercaseaux, W. Nawrocki, J. Gallicchio, C. Codel, M. Carneiro, M. Heule, אימות ב-Lean של משפט המשושה הריק, ITP 2024.
- **BB(5)**, bbchallenge (הודעה ביולי 2024; הוכחה ב-Coq). https://bbchallenge.org

## 2. מוכיחי משפטים נוירוניים ומערכות AI למתמטיקה

- GPT-f (Polu, Sutskever, 2020). https://arxiv.org/abs/2009.03393
- miniF2F (2021). https://arxiv.org/abs/2109.00110
- HTPS (Lample et al., 2022). https://arxiv.org/abs/2205.11491
- LeanDojo / ReProver (Yang et al., 2023). https://arxiv.org/abs/2306.15626
- PutnamBench (Tsoukalas et al., 2024). https://arxiv.org/abs/2407.11214
- DeepSeek-Prover V1 / V1.5 / V2. https://arxiv.org/abs/2405.14333 ; https://arxiv.org/abs/2408.08152 ; https://arxiv.org/abs/2504.21801
- Goedel-Prover (2025). https://arxiv.org/abs/2502.07640
- Kimina-Prover (2025). https://arxiv.org/abs/2504.11354
- Seed-Prover (ByteDance, 2025). https://arxiv.org/abs/2507.23726 ; https://seed.bytedance.com/en/blog/bytedance-seed-prover-achieves-silver-medal-score-in-imo-2025
- AlphaGeometry (Trinh et al.), Nature 625 (2024). https://www.nature.com/articles/s41586-023-06747-5
- AlphaProof, IMO 2024. https://deepmind.google/discover/blog/ai-solves-imo-problems-at-silver-medal-level/
- AlphaProof (Hubert et al.), Nature (2025-11-12). https://www.nature.com/articles/s41586-025-09833-y
- Harmonic Aristotle (2025). https://arxiv.org/abs/2510.01346
- Gemini Deep Think, IMO 2025. https://deepmind.google/discover/blog/advanced-version-of-gemini-with-deep-think-officially-achieves-gold-medal-standard-at-the-international-mathematical-olympiad/
- First Proof (2026). https://1stproof.org/ ; https://arxiv.org/abs/2602.05192 ; https://ethz.ch/staffnet/en/news-and-events/internal-news/archive/2026/07/eth-team-wins-first-proof-challenge-for-ai-assisted-mathematical-research.html [לא אומת: תוצאות סבב 3 מול הדוח הרשמי]
- W. McCune, פתרון השערת Robbins במוכיח EQP, J. Automated Reasoning 19 (1997).

## 3. חיפוש, גילוי ובנייה בעזרת מחשב

- A. Z. Wagner, "Constructions in combinatorics via neural networks" (2021). https://arxiv.org/abs/2104.14516
- G. Raayoni et al., Ramanujan Machine, Nature 590 (2021). https://www.nature.com/articles/s41586-021-03229-4
- A. Davies et al., ML מנחה קשרים ותורת הצגות, Nature 600 (2021). https://www.nature.com/articles/s41586-021-04086-x
- A. Fawzi et al., AlphaTensor, Nature 610 (2022).
- B. Romera-Paredes et al., FunSearch, Nature 625 (2024). https://www.nature.com/articles/s41586-023-06924-6
- F. Charton, J. Ellenberg, A. Z. Wagner, G. Williamson, PatternBoost (2024). https://arxiv.org/abs/2411.00566
- DeepMind, AlphaEvolve (מאי 2025). https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/ ; https://arxiv.org/abs/2506.13131
- B. Georgiev, J. Gómez-Serrano, T. Tao, A. Z. Wagner (2025), AlphaEvolve על 67 בעיות. https://arxiv.org/abs/2511.02864

### SAT והוכחות ממוחשבות

- K. Appel, W. Haken, משפט ארבעת הצבעים, Illinois J. Math. 21 (1977).
- T. Hales, "A proof of the Kepler conjecture", Annals 162 (2005).
- B. Konev, A. Lisitsa, אי-התאמה של ארדש ב-SAT, SAT 2014.
- M. Heule, O. Kullmann, V. Marek, שלשות פיתגוריות בוליאניות, SAT 2016.
- M. Heule, "Schur Number Five", AAAI 2018.
- A. de Grey, צביעת המישור, Geombinatorics 28 (2018).
- J. Brakensiek, M. Heule, J. Mackey, D. Narváez, השערת Keller במימד 7, IJCAR 2020.
- G. Gardam, דוגמה נגדית להשערת היחידות של Kaplansky, Annals 194 (2021).
- B. Bašić, מספר Heesch 6, Discrete Comput. Geom. 65 (2021).
- M. Heule, M. Scheucher, משפט המשושה הריק, TACAS 2024.
- J. Steininger, S. Yurkevich, Noperthedron (2025). https://arxiv.org/abs/2508.18475

## 4. בעיות ארדש

- ויקי תרומות AI לבעיות ארדש (Tao ושותפים; עודכן עד 30 ביוני 2026). https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems
- erdosproblems.com (Thomas Bloom). https://www.erdosproblems.com
- בעיה #728, תיאור הפתרון (ינואר 2026). https://arxiv.org/abs/2601.07421
- סיקור פרשת אוקטובר 2025. https://www.eweek.com/news/openai-math-hype/
- T. Tao, פתרון בעיית אי-ההתאמה של ארדש, Discrete Analysis 2016:1.

## 5. בנצ'מרקים

- FrontierMath (Epoch AI). https://epoch.ai/frontiermath
- מחלוקת המימון של FrontierMath (ינואר 2025). https://techcrunch.com/2025/01/19/ai-benchmarking-organization-criticized-for-waiting-to-disclose-funding-from-openai
- Humanity's Last Exam. https://lastexam.ai/ [לא אומת: שיעור התשובות השגויות לפי ביקורות מאוחרות]

## 6. הוכחות יצירתיות קלאסיות ומודרניות

הרשימה מאחדת את המקורות של `data/creative_proofs.csv`, לפי סדר כרונולוגי. המזהה בסוגריים מפנה לשורה בקובץ.

- Euclid, *Elements*, ספר IX, טענה 20 (P001).
- Archimedes, *The Method*; J. L. Heiberg (1906); R. Netz, W. Noel, *The Archimedes Codex* (2007) (P002).
- Johann Bernoulli, Acta Eruditorum (1697) (P003).
- L. Euler, "Solutio problematis ad geometriam situs pertinentis" (1736) (P004).
- C. F. Gauss, *Disquisitiones Arithmeticae* (1801), פרק VII (P005).
- P. G. L. Dirichlet, Abh. Königl. Preuss. Akad. Wiss. (1837) (P006).
- É. Galois, כתבי יד, פורסמו על ידי Liouville (1846) (P007).
- W. W. Johnson, W. E. Story, Amer. J. Math. 2 (1879) (P009).
- G. Cantor, Jahresber. DMV 1 (1891) (P008).
- M. Dehn, Math. Ann. 55 (1901) (P010).
- E. Sperner, Abh. Math. Sem. Hamburg 6 (1928) (P011).
- K. Gödel, Monatsh. Math. Phys. 38 (1931) (P012).
- M. Black, *Critical Thinking* (1946); J. McCarthy (1964) (P013).
- P. Erdős, Bull. AMS 53 (1947) (P014).
- H. Furstenberg, Amer. Math. Monthly 62 (1955) (P015); J. Analyse Math. 31 (1977) (P018).
- D. Schattschneider, על המחומשים של Marjorie Rice, Math. Magazine 51 (1978) (P019).
- P. Candelas, X. de la Ossa, P. Green, L. Parkes, Nucl. Phys. B 359 (1991) (P020).
- R. Borcherds, Invent. Math. 109 (1992) (P021).
- A. Wiles, Annals 141 (1995); R. Taylor, A. Wiles, Annals 141 (1995) (P022).
- G. Perelman (2002–2003). https://arxiv.org/abs/math/0211159 ; https://arxiv.org/abs/math/0303109 ; https://arxiv.org/abs/math/0307245 (P026)
- Z. Dvir, J. AMS 22 (2009) (P027).
- D.H.J. Polymath, Annals 175 (2012) (P031); Res. Math. Sci. 1 (2014) (P030).
- Y. Zhang, Annals 179 (2014) (P028).
- J. Maynard, Annals 181 (2015) (P029).
- J. Ellenberg, D. Gijswijt, Annals 185 (2017); E. Croot, V. Lev, P. P. Pach, Annals 185 (2017) (P035).
- M. Viazovska, Annals 185 (2017); H. Cohn et al., Annals 185 (2017) (P036).
- H. Huang, Annals 190 (2019) (P038).
- D. Smith, J. S. Myers, C. S. Kaplan, C. Goodman-Strauss, "An aperiodic monotile", Combinatorial Theory 4 (2024). https://arxiv.org/abs/2303.10798 (P048)
- H. Wang, J. Zahl, Kakeya ב-$\mathbb{R}^3$ (2025). https://arxiv.org/abs/2502.17655 (P055)
- R. B. Nelsen, *Proofs Without Words*, MAA (1993) (P060).

## 7. פיזיקה תיאורטית

### רקע ובעיות פתוחות

- Clay Mathematics Institute, Millennium Problems. https://www.claymath.org/millennium-problems/
- A. Jaffe, F. Quinn, "'Theoretical mathematics': Toward a cultural synthesis of mathematics and theoretical physics", Bull. AMS 29 (1993). (מצוטט בפרק 10 בלבד, לא במסמכי `docs/`.)
- Navier–Stokes existence and smoothness. https://en.wikipedia.org/wiki/Navier%E2%80%93Stokes_existence_and_smoothness
- J. Chen, T. Hou, התפוצצות של אוילר בעזרת מחשב (2022–2023). https://arxiv.org/abs/2210.07191
- Wang et al. (2025), גילוי סינגולריות לא-יציבות בעזרת PINNs [לא אומת: preprint, מזהה לא צוין במסמכים].

### Conformal bootstrap

- S. El-Showk et al. (2014). https://arxiv.org/abs/1403.4545
- F. Kos, D. Poland, D. Simmons-Duffin, A. Vichi, "Precision islands in the Ising and O(N) models" (2016). https://arxiv.org/abs/1603.04436
- C.-H. Chang et al., "Bootstrapping the 3d Ising stress tensor" (2024) [לא אומת: ערכים מדויקים].
- D. Simmons-Duffin, SDPB. https://arxiv.org/abs/1502.02033 ; https://github.com/davidsd/sdpb

### אמפליטודות, הולוגרפיה ואינטגרביליות

- N. Arkani-Hamed, J. Trnka, "The Amplituhedron" (2013). https://arxiv.org/abs/1312.2007
- Guevara, Lupsasca, Skinner, Strominger, Weil, "Single-minus gluon tree amplitudes are nonzero" (2026). סיקור: https://phys.org/news/2026-02-chatbot-author-ai-stalled-gluon.html ; ניתוח ביקורתי: https://huggingface.co/blog/dlouapre/gpt-single-minus-gluons
- F. Pastawski, B. Yoshida, D. Harlow, J. Preskill, קוד HaPPY (2015). https://arxiv.org/abs/1503.06237
- M. de Leeuw, A. Pribytok, P. Ryan, "Classifying integrable spin-1/2 chains with nearest neighbour interactions" (2019).

### למידת מכונה בפיזיקה

- S.-M. Udrescu, M. Tegmark, "AI Feynman", Science Advances (2020). https://www.science.org/doi/10.1126/sciadv.aay2631
- M. Cranmer, PySR (2023). https://github.com/MilesCranmer/PySR
- Normalizing flows ל-lattice field theory (Albergo, Kanwar, Shanahan, 2019). https://arxiv.org/abs/1904.12072
- Y.-H. He, ML ב-string landscape (2017). https://arxiv.org/abs/1706.02714
- J. Carifio, J. Halverson, D. Krioukov, B. Nelson (2017). https://arxiv.org/abs/1707.00655

### פיזיקה ב-Lean

- J. Tooby-Smith, "HepLean: Digitalising high energy physics", Comput. Phys. Commun. 308 (2025) 109457. https://arxiv.org/abs/2405.08863 ; https://physlean.com/ ; https://github.com/HEPLean/PhysLean

### מטרות P בבנק (`data/goals.csv`)

- G069, Smale 6: Albouy–Kaloshin, Annals 176 (2012). https://annals.math.princeton.edu/2012/176-1/p10 ; https://en.wikipedia.org/wiki/Smale%27s_problems
- G070, השערת Haldane. https://en.wikipedia.org/wiki/Haldane_conjecture ; Gosset–Mozgunov (2016).
- G071, חוק השטח: M. Hastings (2007). https://arxiv.org/abs/0705.2024
- G072, אי-שוויוני Bell: K. F. Pál, T. Vértesi, Phys. Rev. A 82, 022116 (2010).
- G073, Lieb–Thirring: Frank–Hundertmark–Jex–Nam (2021); Frank–Gontier–Lewin (2021).
- G074, הבעיה השישית של הילברט: Deng, Hani, Ma (2025). https://arxiv.org/abs/2503.01800 [בבדיקה בקהילה]
- G075, הליכה עצמית-נמנעת. https://arxiv.org/abs/1007.0575
- G076, יציבות Kerr: Klainerman, Szeftel, Giorgi (2022). https://arxiv.org/abs/2205.14808

## 8. בנק המטרות: מקורות למטרות הראשונות

- G050: https://en.wikipedia.org/wiki/Schur_number ; https://en.wikipedia.org/wiki/Van_der_Waerden_number ; L. D. Baumert (1965); V. Chvátal (1970); https://lean-lang.org/
- G023, G052: erdosproblems.com, ויקי תרומות ה-AI (סעיף 4), ו-Formal Conjectures (DeepMind). https://github.com/google-deepmind/formal-conjectures
- G029, G027: טבלאות Rabung–Lotts ו-Monroe ל-$W(r,k)$; S. Radziszowski, "Small Ramsey Numbers" (סקר דינמי, Electronic Journal of Combinatorics) [לא אומת: המסמכים לא נותנים URL].

## 9. גשרי חוכמה: מקורות יהודיים, היסטוריה של המתמטיקה ומתודולוגיה

### מקורות יהודיים

- רמב"ם, הקדמה לשמונה פרקים ("שמע האמת ממי שאמרה").
- רמב"ם, משנה תורה, ספר זמנים, הלכות קידוש החודש (פרקים ו–י: חשבון הלוח הקבוע; יא–יט: ראיית הלבנה; יז, כד: עיקרון הראיות). [יז, כד אומת דרך מקורות משניים, למשל https://outorah.org/p/47556 ; החלוקה בין הפרקים לא אומתה מול הטקסט]
- ספר יצירה, נוסחים שונים; A. Kaplan, *Sefer Yetzirah: The Book of Creation in Theory and Practice* (1990). "שתי אבנים בונות שני בתים": משנה 4:12 במספור Kaplan (נוסח הגר"א). [לא אומת מול טקסט עברי]
- תלמוד בבלי, תענית כג ע"א ("או חברותא או מיתותא").
- משנה, אבות ג, יח ("תקופות וגימטריאות פרפראות לחכמה"). https://www.yeshiva.org.il/wiki/index.php/גימטריה
- ברייתא דרבי ישמעאל (שלוש-עשרה מידות), פתיחת הספרא.
- רבי לוי בן גרשום (רלב"ג), *מעשה חושב* (1321).
- רבי משה חיים לוצאטו (רמח"ל), *קל"ח פתחי חכמה*; *דרך ה'*; *דרך תבונות*.
- רבי שלום שרעבי (הרש"ש), *נהר שלום*; סידור הרש"ש (הכוונות).
- אברהם אבן עזרא, *ספר המספר*.

### היסטוריה ופילוסופיה של המתמטיקה

- I. Lakatos, *Proofs and Refutations*, Cambridge University Press (1976).
- N. L. Rabinovitch, *Probability and Statistical Inference in Ancient and Medieval Jewish Literature*, University of Toronto Press (1973).
- D. F. Mansfield, N. J. Wildberger, "Plimpton 322 is Babylonian exact sexagesimal trigonometry", Historia Mathematica 44 (2017); והביקורת של E. Robson ואחרים.
- B. Cutler, ספירת סידורי ה-Stomachion (2003): 17,152 סידורים, 536 עד כדי סימטריה.
- E. M. Reingold, N. Dershowitz, *Calendrical Calculations*, Cambridge University Press.
- Pingala, *Chandaḥśāstra*; Halayudha (המאה ה-10); Madhava ובית הספר של קרלה; *Sunzi Suanjing*; Qin Jiushao (1247); אל-ח'וארזמי, *al-jabr wa'l-muqābala* (כ-820).

### מתודולוגיה סטטיסטית

- D. Witztum, E. Rips, Y. Rosenberg, Statistical Science 9 (1994).
- B. McKay, D. Bar-Natan, M. Bar-Hillel, G. Kalai, "Solving the Bible Code Puzzle", Statistical Science 14 (1999).

## 10. כלים

הקטלוג המלא (140 כלים, 19 קטגוריות) נמצא ב-`data/tools.csv`. כאן מופיעים הכלים שהספר מזכיר.

### עוזרי הוכחות וספריות Lean

- Lean 4: https://lean-lang.org ; elan: https://github.com/leanprover/elan ; Lake: https://github.com/leanprover/lean4/tree/master/src/lake
- mathlib4: https://github.com/leanprover-community/mathlib4
- LeanSearch: https://leansearch.net ; Loogle: https://loogle.lean-lang.org
- Lean REPL: https://github.com/leanprover-community/repl ; lean-lsp-mcp: https://github.com/oOo0oOo/lean-lsp-mcp
- leanblueprint: https://github.com/PatrickMassot/leanblueprint
- LeanDojo: https://github.com/lean-dojo/LeanDojo
- lean-action (CI): https://github.com/leanprover/lean-action
- Isabelle/HOL: https://isabelle.in.tum.de ; Rocq (לשעבר Coq): https://rocq-prover.org ; HOL Light: https://github.com/jrh13/hol-light

### SAT, SMT וחיפוש

- CaDiCaL: https://github.com/arminbiere/cadical ; Kissat: https://github.com/arminbiere/kissat
- DRAT-trim: https://github.com/marijnheule/drat-trim ; cake_lpr: https://github.com/tanyongkiam/cake_lpr
- PySAT: https://pysathq.github.io ; Z3: https://github.com/Z3Prover/z3
- OpenEvolve: https://github.com/codelion/openevolve

### אלגברה ממוחשבת ונומריקה

- SageMath: https://www.sagemath.org ; PARI/GP: https://pari.math.u-bordeaux.fr ; SymPy: https://www.sympy.org
- FLINT: https://flintlib.org ; Arb: https://arblib.org ; mpmath: https://mpmath.org ; NetworkX: https://networkx.org
- SDPB, PySR, AI Feynman: ראו סעיף 7. AI Feynman (קוד): https://github.com/SJ001/AI-Feynman

### מודלים ותשתית סוכנים

- Claude API: https://docs.anthropic.com ; Claude Agent SDK: https://docs.anthropic.com/en/docs/claude-code/sdk ; Claude Code: https://docs.anthropic.com/en/docs/claude-code/overview
- Model Context Protocol: https://modelcontextprotocol.io

### ספרות ונתונים

- arXiv: https://arxiv.org ; arXiv API: https://info.arxiv.org/help/api/index.html
- zbMATH Open: https://zbmath.org ; Semantic Scholar API: https://www.semanticscholar.org/product/api ; Google Scholar: https://scholar.google.com
- OEIS: https://oeis.org ; LMFDB: https://www.lmfdb.org

### טקסטים עבריים

- Sefaria API: https://developers.sefaria.org ; Sefaria-Export: https://github.com/Sefaria/Sefaria-Export
- Dicta: https://dicta.org.il ; HebrewBooks.org: https://hebrewbooks.org
- אוצר החכמה: https://www.otzar.org ; פרויקט השו"ת של בר-אילן: https://www.responsa.co.il

## 11. מקורות פנימיים של המעבדה

- מעקב בנק המטרות ב-Google Sheets: https://docs.google.com/spreadsheets/d/1V9coJlUiul7Z8uRsovujRcw9KB6DWcYMtOQhWudvhNo/edit
- `lab/README.md`, `docs/*.md`, `data/*.csv`, `news/README.md`, `site/README.md`.

## בקצרה

- הנספח מאחד את המקורות של כל המסמכים ב-`docs/` ושל קובצי הנתונים, בלי כפילויות, לפי אחד-עשר נושאים.
- מקורות שלא נקראו ישירות או שפרטיהם לא נבדקו מסומנים [לא אומת], כמו במסמכי המקור.
- כשמסמך מציין רק מזהה arXiv, הקישור נבנה ממנו; ספרים ומאמרים בלי קישור מופיעים עם פרטי הפרסום.
- כל מקור חדש בפרק מתווסף גם לכאן, בסעיף המתאים.

## רעיונות לתוכן

1. **"ספריית המעבדה": עמוד באתר.** הביבליוגרפיה כרשימה מסוננת לפי נושא, עם קישור לפרקים שמצטטים כל מקור. קהל יעד: סטודנטים וחוקרים שמצטרפים למעבדה.
2. **"עשרה מאמרים שכל מי שעוסק ב-AI למתמטיקה צריך לקרוא": פוסט.** בחירה מסעיפים 1–3 עם משפט הסבר לכל מאמר. קהל יעד: מהנדסי AI, סטודנטים לתארים מתקדמים.
3. **"מספר יצירה ועד FunSearch": שרשור.** קו זמן של מקורות מהנספח, מהעת העתיקה ועד 2026, בלי לטעון לקשר סיבתי ביניהם. קהל יעד: קהל רחב שמתעניין בהיסטוריה של המדע.
