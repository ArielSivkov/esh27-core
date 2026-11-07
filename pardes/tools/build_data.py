#!/usr/bin/env python3
"""Build the JSON data files for the Pardes Rimonim site from the source text.

Usage:  python3 pardes/tools/build_data.py
Reads   pardes/source/pardes_rimonim.txt
Writes  pardes/data/*.json and pardes/data/gates/<n>.json

Every number this script produces is a mechanical count over the text
(regex matches, co-occurrence within a paragraph). These counts are
approximations meant to guide study, not scholarly conclusions.
"""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source" / "pardes_rimonim.txt"
OUT = ROOT / "data"

HEB_VAL = {"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
           "י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80,
           "צ": 90, "ק": 100, "ר": 200, "ש": 300, "ת": 400}


def heb_num(s):
    return sum(HEB_VAL.get(c, 0) for c in s)


def num_heb(n):
    out = ""
    for v, c in [(400, "ת"), (300, "ש"), (200, "ר"), (100, "ק"), (90, "צ"), (80, "פ"),
                 (70, "ע"), (60, "ס"), (50, "נ"), (40, "מ"), (30, "ל"), (20, "כ"), (10, "י")]:
        while n >= v:
            out += c
            n -= v
    if out.endswith("י") and n in (5, 6):
        out = out[:-1] + {5: "טו", 6: "טז"}[n]
        n = 0
    if n:
        out += "אבגדהוזחט"[n - 1]
    return out


GATE_TITLES = {
    1: "עשר ולא תשע", 2: "טעם האצילות", 3: "אם אין סוף הוא הכתר", 4: "עצמות וכלים",
    5: "סדר האצילות", 6: "סדר עמידתן", 7: "הצנורות", 8: "מהות והנהגה",
    9: "המכריעין", 10: "הגוונים", 11: "הצחצחות", 12: "הנתיבות",
    13: "שערים (נ' שערי בינה)", 14: "המציאות", 15: "ממטה למעלה", 16: 'אבי"ע',
    17: "ירך יעקב", 18: "מיעוט הירח", 19: "שם בן ד'", 20: "השמות",
    21: "פרטי השמות", 22: "הכנויים", 23: "ערכי הכנויים", 24: "ההיכלות",
    25: "התמורות (הקליפות)", 26: "היכלות התמורות", 27: "האותיות", 28: "הנקודות",
    29: "הטעמים", 30: "הצירוף", 31: "הנשמה", 32: "הכוונה",
}

P = r'(?<![א-ת"\'])[ובכלמשהד]{0,3}'   # allowed one-letter prefixes
E = r'(?![א-ת])'

SEFIROT = [
    ("keter", "כתר", r'כתר'),
    ("chochma", "חכמה", r'חכמה'),
    ("bina", "בינה", r'בינה'),
    ("chesed", "חסד", r'(?:חסד|גדולה)'),
    ("gevura", "גבורה", r'(?:גבורה|פחד)'),
    ("tiferet", "תפארת", r'(?:תפארת|ת"ת)'),
    ("netzach", "נצח", r'נצח'),
    ("hod", "הוד", r'הוד'),
    ("yesod", "יסוד", r'יסוד'),
    ("malchut", "מלכות", r'(?:מלכות|מל\')'),
]
SEF_RE = {k: re.compile(P + pat + E) for k, _, pat in SEFIROT}

SOURCES = [
    ("zohar", 'זוהר / רשב"י', r'(?:זהר|זוהר|הרשב"י|רשב"י)'),
    ("tikkunim", "תיקוני הזוהר", r'(?:תיקונים|תקונים|תקונא|תיקונא|תקוני|תיקוני)'),
    ("raya", "רעיא מהימנא", r'רעיא מהימנא'),
    ("neelam", "מדרש הנעלם", r'מדרש הנעלם'),
    ("yetzira", "ספר יצירה", r'(?:ספר יצירה|ס\' יצירה|ס"י)'),
    ("bahir", "ספר הבהיר", r'בהיר'),
    ("ramban", 'רמב"ן', r'רמב"ן'),
    ("rashba", 'רשב"א', r'רשב"א'),
    ("raavad", 'ראב"ד', r'ראב"ד'),
    ("recanati", "רקנאטי", r'(?:רקאנטי|רקנאטי|ריקאנטי|ריקנאטי)'),
    ("chayat", "ר' יהודה חייט", r'חייט'),
    ("gikatilla", "שערי אורה / ג'יקטיליא", r'(?:שערי אורה|גקטיליא|ג\'יקטיליא|גיקטיליא|גיקטילייא)'),
    ("hashem", "ספר השם", r'ספר השם'),
    ("maarechet", "מערכת האלהות", r'מערכת'),
    ("azriel", "ר' עזריאל", r'עזריאל'),
    ("akiva", "רבי עקיבא", r'(?:רבי עקיבא|ר"ע)'),
    ("geonim", "הגאונים", r'(?:גאון|הגאונים)'),
]
SRC_RE = {k: re.compile(pat) for k, _, pat in SOURCES}

# names of the gates as they are referred to inside the book
REF_NAMES = {
    'אבי"ע': 16, "הצנורות": 7, "הצינורות": 7, "המכריעין": 9, "המכריעים": 9,
    "הגוונים": 10, "הצחצחות": 11, "הנתיבות": 12, "המציאות": 14, "המציאיות": 14,
    "השמות": 20, "הכנויים": 22, "הכינויים": 22, "ערכי": 23, "ההיכלות": 24,
    "התמורות": 25, "האותיות": 27, "הנקודות": 28, "הטעמים": 29, "הצירוף": 30,
    "הצרוף": 30, "הנשמה": 31, "הכוונה": 32, "עצמות": 4, "מהות": 8, "ממטה": 15,
    "מיעוט": 18, "ירך": 17, "פרטי": 21, "טעם": 2,
}
ORD = {"הראשון": 1, "השני": 2, "השלישי": 3, "הרביעי": 4, "החמישי": 5, "הששי": 6,
       "השביעי": 7, "השמיני": 8, "התשיעי": 9, "העשירי": 10}

HDR = re.compile(r'^שער ([א-ת]+) פרק ([א-ת]+)\s*$')
CHAP_LABEL = re.compile(r'^פרק [א-ת"\' ]+:?\s*$')


def parse():
    lines = SRC.read_text(encoding="utf-8").split("\n")
    gates = {}
    cur_g = 0
    cur = None
    for raw in lines:
        line = raw.replace("\xa0", " ").strip()
        if not line or line.startswith("http"):
            continue
        m = HDR.match(line)
        if m:
            g = heb_num(m.group(1))
            if g not in (cur_g, cur_g + 1):     # typo in a header: keep current gate
                g = cur_g
            cur_g = g
            gates.setdefault(g, [])
            cur = {"n": len(gates[g]) + 1, "paras": []}
            gates[g].append(cur)
            continue
        if cur is None or CHAP_LABEL.match(line):
            continue
        cur["paras"].append(line)
    return gates


def count_sef(text):
    return {k: len(r.findall(text)) for k, r in SEF_RE.items()}


def tokenize(text):
    return re.findall(r'[א-ת][א-ת"\']*[א-ת]', text)


def find_refs(text, g):
    refs = []
    for m in re.finditer(r'(?:ב|ל|מ|ו)?שער\s+([א-ת"\']+)', text):
        w = m.group(1).strip("'")
        t = None
        if w in REF_NAMES:
            t = REF_NAMES[w]
        elif w in ORD:
            t = ORD[w]
        elif w in ("הקודם",):
            t = g - 1
        elif re.fullmatch(r'[א-ל]{1,2}', w.replace('"', "")) and ('"' in m.group(1) or "'" in m.group(1)):
            t = heb_num(w.replace('"', ""))
        if t and 1 <= t <= 32 and t != g:
            refs.append(t)
    return refs


def main():
    gates = parse()
    assert len(gates) == 32, len(gates)
    OUT.mkdir(exist_ok=True)
    (OUT / "gates").mkdir(exist_ok=True)

    meta = []
    gate_tokens = {}
    ref_edges = Counter()
    sef_by_gate = {}
    src_by_gate = {}
    pair_by_gate = {}
    toc = []
    for g in range(1, 33):
        chs = gates[g]
        text = "\n".join(p for c in chs for p in c["paras"])
        toks = tokenize(text)
        gate_tokens[g] = Counter(toks)
        sef_by_gate[g] = count_sef(text)
        src_by_gate[g] = {k: len(r.findall(text)) for k, r in SRC_RE.items()}
        for t in find_refs(text, g):
            ref_edges[(g, t)] += 1
        # sefirah co-occurrence within a paragraph
        pc = Counter()
        for c in chs:
            for p in c["paras"]:
                present = [k for k, r in SEF_RE.items() if r.search(p)]
                for i in range(len(present)):
                    for j in range(i + 1, len(present)):
                        pc[(present[i], present[j])] += 1
        pair_by_gate[g] = pc
        intro = ""
        for p in chs[0]["paras"][:4]:
            if re.search(r'(הנרצה|הכוונה|נרצה)', p):
                intro = p
                break
        if not intro and chs[0]["paras"]:
            intro = chs[0]["paras"][0]
        meta.append({
            "n": g, "heb": num_heb(g), "title": GATE_TITLES[g], "intro": intro,
            "chapters": len(chs), "paras": sum(len(c["paras"]) for c in chs),
            "words": len(toks),
            "chapterOpenings": [(c["paras"][0][:140] if c["paras"] else "") for c in chs],
        })
        (OUT / "gates" / f"{g}.json").write_text(json.dumps(
            {"n": g, "heb": num_heb(g), "title": GATE_TITLES[g],
             "chapters": [{"n": c["n"], "heb": num_heb(c["n"]), "paras": c["paras"]} for c in chs]},
            ensure_ascii=False), encoding="utf-8")
        for c in chs:
            toc.append([g, c["n"]])

    # distinctive terms per gate (tf-idf over gates)
    df = Counter()
    for g in gate_tokens:
        df.update(set(gate_tokens[g]))
    for m in meta:
        tc = gate_tokens[m["n"]]
        total = sum(tc.values()) or 1
        scored = []
        for w, c in tc.items():
            if c < 4 or len(w.replace('"', "")) < 3:
                continue
            idf = math.log(33 / df[w])
            if idf < 0.4:
                continue
            scored.append((c / total * idf, w, c))
        scored.sort(reverse=True)
        m["terms"] = [[w, c] for _, w, c in scored[:30]]

    total_words = {g: sum(gate_tokens[g].values()) for g in gate_tokens}
    stats = {
        "sefirot": [{"key": k, "name": n} for k, n, _ in SEFIROT],
        "sources": [{"key": k, "name": n} for k, n, _ in SOURCES],
        "sefByGate": {g: sef_by_gate[g] for g in sef_by_gate},
        "srcByGate": {g: src_by_gate[g] for g in src_by_gate},
        "words": total_words,
        "refs": [[a, b, c] for (a, b), c in sorted(ref_edges.items())],
        "pairsByGate": {g: [[a, b, c] for (a, b), c in pair_by_gate[g].most_common()] for g in pair_by_gate},
    }

    # ---- gate 23: dictionary of kinuyim -----------------------------------
    stop = re.compile(r"\s(?:פי'|פירוש|פירושו|פי\"|הוא|היא|הם|נק'|נקרא|נקראת|נקראו|יש|כנוי|לשון|ענינו|עניינו|ירצה|כענין|ר\"ל|בזהר|כי|מלשון|ענין|ידוע|מבואר|בתיקונים|פירשו|פירש|והטעם|וכולם|מצד|בסוד|שהוא|שהיא)(?=\s|$)")
    entries = []
    letters = "אבגדהוזחטיכלמנסעפצקרשת"
    for ci, c in enumerate(gates[23]):
        letter = letters[ci] if ci < 22 else "?"
        for pi, p in enumerate(c["paras"]):
            if ci == 0 and pi < 2:
                continue  # gate introduction
            body = p
            sub = False
            mm = re.match(r"^(?:עוד|ועוד|ולפעמים|ויש)\s+(?:נקראת|נקרא|נק'|יש|יקרא|תקרא|נקראו)?\s*", p)
            if mm and mm.end() > 3:
                sub = True
                body = p[mm.end():]
            cut = stop.search(" " + body)
            head = (" " + body)[: cut.start()].strip() if cut else " ".join(body.split()[:2])
            head = re.split(r"[.,:(\[]", head)[0].strip()
            words = head.split()
            if not words or len(words) > 4:
                head = " ".join(body.split()[:2])
            sc = count_sef(p)
            ranked = [k for k, v in sorted(sc.items(), key=lambda kv: -kv[1]) if v]
            entries.append({"l": letter, "t": head, "sub": sub, "s": ranked[:3],
                            "x": p, "c": c["n"], "p": pi})
    (OUT / "kinuyim.json").write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")

    # ---- generic co-occurrence lexicons for specific gates ---------------------
    def lexicon(gate_list, items):
        """items: list of (key, label, regex). Returns counts, sefirah co-occurrence and quotes."""
        out = []
        for key, label, pat in items:
            r = re.compile(pat)
            cnt = 0
            co = Counter()
            quotes = []
            for g in gate_list:
                for c in gates[g]:
                    for pi, p in enumerate(c["paras"]):
                        hits = len(r.findall(p))
                        if not hits:
                            continue
                        cnt += hits
                        for k, sr in SEF_RE.items():
                            if sr.search(p):
                                co[k] += 1
                        if len(quotes) < 6:
                            mm = r.search(p)
                            s = max(0, mm.start() - 90)
                            quotes.append({"g": g, "c": c["n"], "p": pi,
                                           "q": ("…" if s else "") + p[s: mm.end() + 160] + "…"})
            out.append({"key": key, "label": label, "count": cnt, "co": co, "quotes": quotes})
        return out

    colors = lexicon([10], [
        ("white", "לבן", r'(?:לבן|לובן|לבנונית|חוור|חיור|חיוור)'),
        ("red", "אדום", r'(?:אדום|אודם|אדמימות|סומק|סומקא)'),
        ("green", "ירוק", r'(?:ירוק|ירוקה|ירקרק|ירקות)'),
        ("black", "שחור", r'(?:שחור|שחורה|שחרות|אוכם|אוכמא)'),
        ("blue", "תכלת", r'(?:תכלת|כחול|תכלא)'),
        ("gold", "זהב", r'זהב'),
        ("silver", "כסף", r'כסף'),
        ("sapphire", "ספיר", r'ספיר'),
        ("purple", "ארגמן", r'ארגמן'),
        ("yellow", "צהוב", r'(?:צהוב|צהבהב)'),
    ])
    letters_lex = lexicon([27], [
        ("alef", "א", r'אל"ף'), ("bet", "ב", r'בי"ת'), ("gimel", "ג", r'גימ"ל'),
        ("dalet", "ד", r'דל"ת'), ("he", "ה", r'ה"א'), ("vav", "ו", r'וא"ו|ו"ו'),
        ("zayin", "ז", r'זי"ן'), ("chet", "ח", r'חי"ת'), ("tet", "ט", r'טי"ת'),
        ("yod", "י", r'יו"ד'), ("kaf", "כ", r'כ"ף'), ("lamed", "ל", r'למ"ד'),
        ("mem", "מ", r'מ"ם'), ("nun", "נ", r'נו"ן'), ("samech", "ס", r'סמ"ך'),
        ("ayin", "ע", r'עי"ן'), ("pe", "פ", r'פ"א|פ"ה'), ("tzadi", "צ", r'צד"י|צד"ק'),
        ("kuf", "ק", r'קו"ף'), ("resh", "ר", r'רי"ש'), ("shin", "ש", r'שי"ן'),
        ("tav", "ת", r'ת"ו|תי"ו'),
    ])
    nikud = lexicon([28], [
        ("kamatz", "קמץ", r'קמץ|קמ"ץ|קמצ'), ("patach", "פתח", r'פתח'),
        ("tzere", "צירי", r'צירי|צרי|צר"י'), ("segol", "סגול", r'סגול|סגו"ל|סגולתא'),
        ("shva", "שבא", r'שבא|שב"א|שוא'), ("cholam", "חולם", r'חולם|חול"ם|חלם'),
        ("chirik", "חירק", r'חירק|חיר"ק|חרק'), ("shuruk", "שורק", r'שורק|שור"ק|שרק'),
        ("kubutz", "קבוץ", r'קבוץ|קבו"ץ|קבוצ'),
    ])
    teamim = lexicon([29], [
        ("zarka", "זרקא", r'זרקא'), ("segolta", "סגולתא", r'סגולתא'), ("pazer", "פזר", r'פזר'),
        ("telisha", "תלישא", r'תלישא'), ("geresh", "גרש / גרשיים", r'גרש|גרשיים|תרי טעמי'),
        ("revia", "רביע", r'רביע'), ("zakef", "זקף", r'זקף'), ("tipcha", "טפחא", r'טפחא|טרחא'),
        ("etnachta", "אתנחתא", r'אתנחתא|אתנח'), ("sofpasuk", "סוף פסוק / סלוק", r'סוף פסוק|סלוק'),
        ("munach", "מונח", r'מונח|מנח'), ("mahpach", "מהפך", r'מהפך'), ("pashta", "פשטא", r'פשטא'),
        ("darga", "דרגא", r'דרגא'), ("tevir", "תביר", r'תביר'), ("yetiv", "יתיב", r'יתיב'),
        ("kadma", "קדמא / אזלא", r'קדמא|אזלא'), ("shalshelet", "שלשלת", r'שלשלת'),
        ("karnei", "קרני פרה", r'קרני פרה'), ("merkha", "מרכא", r'מרכא'),
    ])
    names = lexicon(list(range(1, 33)), [
        ("ehye", "אהיה", r'אהי"ה|אהיה'), ("yah", "יה", r'(?<![א-ת])י"ה(?![א-ת])'),
        ("havaya", 'הוי"ה / ידו"ד', r'הוי"ה|ידו"ד|יהו"ה|בן ד\''),
        ("el", "אל", r'(?<![א-ת])א"ל(?![א-ת])|שם אל'), ("elohim", "אלהים", r'אלהי"ם|אלקים|אלהים|אלדים|אלקי"ם'),
        ("eloha", "אלוה", r'אלו"ה|אלוה|אלוק'), ("tzevaot", "צבאות", r'צבאות|צבאו"ת'),
        ("shaddai", "שדי", r'שד"י|שדי(?![א-ת])'), ("adonai", "אדני", r'אדנ"י|אדני|אדנות'),
        ("72", "שם ע\"ב", r'שם ע"ב|ע"ב שמות|ע"ב תיבות'), ("42", "שם מ\"ב", r'שם מ"ב|מ"ב אותיות'),
    ])
    heichalot = lexicon([24], [
        ("h1", "לבנת הספיר", r'לבנת הספיר'), ("h2", "עצם השמים", r'עצם השמים|עצם שמים'),
        ("h3", "נוגה", r'נוגה|נגה'), ("h4", "זכות", r'זכות'), ("h5", "אהבה", r'אהבה'),
        ("h6", "רצון", r'רצון'), ("h7", "קדש הקדשים", r'קדש הקדשים|קודש הקדשים'),
    ])
    souls = lexicon([31], [
        ("nefesh", "נפש", r'נפש'), ("ruach", "רוח", r'רוח'), ("neshama", "נשמה", r'נשמה'),
        ("chaya", "חיה", r'(?<![א-ת])חיה(?![א-ת])'), ("yechida", "יחידה", r'יחידה'),
        ("tzelem", "צלם", r'צלם'),
    ])
    worlds = lexicon([16], [
        ("atzilut", "אצילות", r'אצילות'), ("beria", "בריאה", r'בריאה'),
        ("yetzira", "יצירה", r'יצירה'), ("asiya", "עשיה", r'עשיה|עשייה'),
    ])
    paths32 = lexicon([12], [
        ("sechel", "שכל (נתיבות השכל)", r'שכל'), ("netiv", "נתיב", r'נתיב'),
    ])

    def fix(lex):
        for e in lex:
            e["co"] = dict(e["co"])
        return lex

    lex = {"colors": fix(colors), "letters": fix(letters_lex), "nikud": fix(nikud),
           "teamim": fix(teamim), "names": fix(names), "heichalot": fix(heichalot),
           "souls": fix(souls), "worlds": fix(worlds), "paths": fix(paths32)}

    (OUT / "meta.json").write_text(json.dumps({"gates": meta, "toc": toc}, ensure_ascii=False), encoding="utf-8")
    (OUT / "stats.json").write_text(json.dumps(stats, ensure_ascii=False), encoding="utf-8")
    (OUT / "lexicons.json").write_text(json.dumps(lex, ensure_ascii=False), encoding="utf-8")
    print("gates", len(meta), "chapters", len(toc), "kinuyim", len(entries),
          "refs", sum(ref_edges.values()))


if __name__ == "__main__":
    main()
