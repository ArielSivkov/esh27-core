#!/usr/bin/env python3
"""Build the ESH27 Lab static site.

Reads ../data/*.csv (+ ../data/ledger.jsonl) and ../news/*.md, embeds everything as
JSON into src/template.html together with src/styles.css and src/app.js, and writes
a single self-contained dist/index.html (plus dist/data.json for other consumers).

Standard library only.  Usage:
    python3 site/build.py                 # build from ../data, sample data as fallback
    python3 site/build.py --no-sample     # never fall back to sample data
    python3 site/build.py --data DIR --news DIR --out DIR
"""
import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
SRC = os.path.join(HERE, "src")
SAMPLE = os.path.join(HERE, "sample_data")

DATASETS = {
    "goals": "goals.csv",
    "creative_proofs": "creative_proofs.csv",
    "tools": "tools.csv",
    "wisdom_projects": "wisdom_projects.csv",
}


def warn(msg):
    print(f"[build] warning: {msg}", file=sys.stderr)


# ---------------------------------------------------------------- data readers
def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):
            row = {}
            for k, v in raw.items():
                if k is None:  # extra unnamed columns
                    warn(f"{os.path.basename(path)} line {i}: extra columns ignored")
                    continue
                if isinstance(v, list):
                    v = ",".join(v)
                row[k.strip()] = (v or "").strip()
            if any(row.values()):
                rows.append(row)
    return rows


def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    out.append(obj)
            except json.JSONDecodeError as e:
                warn(f"ledger.jsonl line {n}: {e}")
    return out


def normalize_goals(rows):
    for r in rows:
        try:
            p = float(str(r.get("progress_pct", "0")).rstrip("%") or 0)
        except ValueError:
            p = 0.0
        r["progress_pct"] = max(0.0, min(100.0, p))
    return rows


# ---------------------------------------------------------------- news (markdown)
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.S)


def parse_front_matter(text):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
        else:
            v = v.strip("'\"")
        meta[k] = v
    return meta, text[m.end():]


def inline_md(s):
    s = html.escape(s, quote=False)
    codes = []

    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
               lambda m: f'<a href="{html.escape(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*$\\])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", s)
    return s


def md_to_html(md):
    """Small, safe Markdown subset: headings, paragraphs, lists, quotes, hr, inline."""
    out, para, lst, quote = [], [], None, []

    def flush_para():
        if para:
            out.append("<p>" + inline_md(" ".join(para)) + "</p>")
            para.clear()

    def flush_list():
        nonlocal lst
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{inline_md(i)}</li>" for i in items) + f"</{tag}>")
            lst = None

    def flush_quote():
        if quote:
            out.append("<blockquote><p>" + inline_md(" ".join(quote)) + "</p></blockquote>")
            quote.clear()

    def flush_all():
        flush_para(); flush_list(); flush_quote()

    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip():
            flush_all()
            continue
        h = re.match(r"^(#{1,4})\s+(.*)$", s)
        ul = re.match(r"^\s*[-*+]\s+(.*)$", s)
        ol = re.match(r"^\s*\d+[.)]\s+(.*)$", s)
        if h:
            flush_all()
            lvl = min(len(h.group(1)) + 1, 5)  # article h1 -> h2 on the page
            out.append(f"<h{lvl}>{inline_md(h.group(2))}</h{lvl}>")
        elif re.match(r"^\s*(---|\*\*\*|___)\s*$", s):
            flush_all()
            out.append("<hr>")
        elif s.startswith(">"):
            flush_para(); flush_list()
            quote.append(s.lstrip("> ").strip())
        elif ul or ol:
            flush_para(); flush_quote()
            tag = "ul" if ul else "ol"
            if not lst or lst[0] != tag:
                flush_list()
                lst = (tag, [])
            lst[1].append((ul or ol).group(1))
        elif lst and line.startswith(("  ", "\t")):
            lst[1][-1] += " " + s.strip()
        else:
            flush_list(); flush_quote()
            para.append(s.strip())
    flush_all()
    return "\n".join(out)


def strip_md(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return re.sub(r"[*_`#>]", "", s).strip()


def read_news(news_dir):
    items = []
    if not os.path.isdir(news_dir):
        return items
    for name in sorted(os.listdir(news_dir)):
        if not name.endswith(".md") or name.lower() == "readme.md":
            continue
        path = os.path.join(news_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                meta, body = parse_front_matter(f.read())
        except OSError as e:
            warn(f"news {name}: {e}")
            continue
        if str(meta.get("draft", "")).lower() == "true":
            continue
        # drop a leading H1 that repeats the title
        body = re.sub(r"^\s*#\s+.*\n", "", body, count=1) if body.lstrip().startswith("# ") else body
        paras = [p for p in re.split(r"\n\s*\n", body) if p.strip() and not p.lstrip().startswith(("#", "-", "*", ">", "|"))]
        excerpt = strip_md(meta.get("summary") or (paras[0] if paras else ""))
        if len(excerpt) > 280:
            excerpt = excerpt[:277].rsplit(" ", 1)[0] + "…"
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        items.append({
            "slug": name[:-3],
            "title": meta.get("title", name[:-3]),
            "date": str(meta.get("date", name[:10])),
            "lang": meta.get("lang", "he"),
            "tags": tags,
            "claim_level": meta.get("claim_level", ""),
            "excerpt": excerpt,
            "html": md_to_html(body),
        })
    return items


# ---------------------------------------------------------------- build
def load_all(data_dir, news_dir, allow_sample):
    data, sources = {}, {}
    for key, fname in DATASETS.items():
        rows, src = [], "none"
        path = os.path.join(data_dir, fname)
        if os.path.isfile(path):
            try:
                rows, src = read_csv(path), "data"
            except (OSError, csv.Error, UnicodeDecodeError) as e:
                warn(f"{fname}: {e}")
        if not rows and allow_sample and os.path.isfile(os.path.join(SAMPLE, fname)):
            rows, src = read_csv(os.path.join(SAMPLE, fname)), "sample"
        data[key] = normalize_goals(rows) if key == "goals" else rows
        sources[key] = src
    ledger_path = os.path.join(data_dir, "ledger.jsonl")
    data["ledger"] = read_jsonl(ledger_path) if os.path.isfile(ledger_path) else []
    sources["ledger"] = "data" if data["ledger"] else "none"
    data["news"] = read_news(news_dir)
    sources["news"] = "data" if data["news"] else "none"
    return data, sources


def render(template, i18n, payload, styles, script):
    he = i18n.get("he", {})

    def tr(m):
        return he.get(m.group(1), m.group(1))

    # {{t:key}} -> Hebrew string (raw HTML allowed; it is our own trusted file).
    # Inside attribute values, quotes must be escaped.
    out = re.sub(r'="\{\{t:([\w.\-]+)\}\}"', lambda m: '="' + html.escape(he.get(m.group(1), m.group(1)), quote=True) + '"', template)
    out = re.sub(r"\{\{t:([\w.\-]+)\}\}", tr, out)
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/").replace("<!--", "<\\!--")
    out = out.replace("{{STYLES}}", styles).replace("{{SCRIPT}}", script).replace("{{DATA_JSON}}", blob)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=os.path.join(LAB, "data"))
    ap.add_argument("--news", default=os.path.join(LAB, "news"))
    ap.add_argument("--out", default=os.path.join(HERE, "dist"))
    ap.add_argument("--no-sample", action="store_true", help="do not fall back to site/sample_data")
    args = ap.parse_args(argv)

    def read(name):
        with open(os.path.join(SRC, name), encoding="utf-8") as f:
            return f.read()

    i18n = json.loads(read("i18n.json"))
    data, sources = load_all(args.data, args.news, not args.no_sample)
    built = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = dict(data)
    payload["i18n"] = i18n
    payload["meta"] = {
        "built_at": built,
        "sources": sources,
        "uses_sample": any(v == "sample" for v in sources.values()),
    }
    page = render(read("template.html"), i18n, payload, read("styles.css"), read("app.js"))

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    public = {k: v for k, v in payload.items() if k != "i18n"}
    with open(os.path.join(args.out, "data.json"), "w", encoding="utf-8") as f:
        json.dump(public, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, ".nojekyll"), "w") as f:
        f.write("")
    # 404 page for static hosts: same app, harmless.
    shutil.copyfile(os.path.join(args.out, "index.html"), os.path.join(args.out, "404.html"))

    counts = ", ".join(f"{k}={len(data[k])}({sources[k]})" for k in list(DATASETS) + ["ledger", "news"])
    print(f"[build] wrote {os.path.relpath(os.path.join(args.out, 'index.html'), os.getcwd())} "
          f"({len(page) // 1024} KB) · {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
