# ESH27 Lab: website

Static, bilingual site (Hebrew first, RTL, with an English toggle) for ESH27 Lab and S27 News.
One Python script (standard library only) reads the lab's data files and writes a single
self-contained `dist/index.html` with the data embedded as JSON. There is no server, no
framework and no npm.

```
site/
├── build.py                 # the build (stdlib: csv, json, re, html)
├── src/
│   ├── template.html        # page skeleton; {{t:key}} = Hebrew string, {{STYLES}}/{{SCRIPT}}/{{DATA_JSON}}
│   ├── styles.css           # design tokens (dark default + light), RTL-safe logical properties
│   ├── app.js               # vanilla JS: i18n toggle, filters/sort, galleries, log, KaTeX
│   └── i18n.json            # all UI strings, {"he": {...}, "en": {...}}
├── sample_data/             # tiny placeholder CSVs, used only when ../data/<file> is missing
├── deploy-pages.yml.example # GitHub Actions workflow (copy into .github/workflows/)
└── dist/                    # build output (index.html, 404.html, data.json, .nojekyll)
```

## Build

```bash
python3 site/build.py                # from lab/; reads ../data and ../news
python3 site/build.py --no-sample    # fail-safe for CI: never show sample data
python3 site/build.py --data DIR --news DIR --out DIR
```

Then open `site/dist/index.html` directly in a browser, or serve it:

```bash
python3 -m http.server -d site/dist 8000
```

### Inputs

| File | Used for | If it is missing |
|---|---|---|
| `data/goals.csv` | hero stats, tier cards, the goal table | sample data, with a "preview" banner |
| `data/creative_proofs.csv` | the creative-proofs gallery | sample data |
| `data/tools.csv` | the toolbox | sample data |
| `data/wisdom_projects.csv` | the wisdom bridges | sample data |
| `data/ledger.jsonl` | the attempts timeline, claim level per goal, the "verified" count | "ledger is empty" placeholder |
| `news/*.md` | S27 News in the progress log (see `news/README.md`) | "no articles yet" |

A malformed row or JSON line produces a warning on stderr and is skipped. The build does
not crash because of one bad row.

### The honesty rules in code

- A goal's claim level is the maximum over ledger attempts that are not `dry_run` and are not
  superseded by a later attempt (`supersedes`).
- An attempt that claims L3 or L4 **without** `certificate.verified == true` is shown as **L2**
  and flagged in the timeline. The site never shows "proved" on the strength of an
  unverified claim.
- `progress_pct` is labelled as work done, not closeness to a proof.

### Editing text and translations

All interface text lives in `src/i18n.json`. The build writes the Hebrew strings into the
HTML, so the page reads correctly before any JavaScript runs. The English toggle swaps them
on the client and remembers the choice in `localStorage`. Data fields are shown as written,
except `title_he`/`title` for goals and the known status and tier values, which are translated.

Formulas: anything between `$…$` or `$$…$$` in the data or articles is typeset by KaTeX
0.16.9 from cdnjs. If the CDN is unreachable, the TeX source stays visible as plain text.

## Deploy

The output is plain static files, so any static host works.

### GitHub Pages (recommended)

1. Copy `site/deploy-pages.yml.example` to `.github/workflows/site.yml` at the repository
   root. Adjust `LAB_DIR` and the `paths:` filters if the lab is not at `lab/`.
2. Repository → Settings → Pages → Source: **GitHub Actions**.
3. Push. The workflow builds with `--no-sample` and publishes `site/dist`.

`.nojekyll` is written so Pages serves the files as they are. `404.html` is a copy of the app.

### Cloud Run (static container)

```bash
python3 site/build.py --no-sample
cat > site/dist/Dockerfile <<'EOF'
FROM nginx:1.27-alpine
COPY . /usr/share/nginx/html
RUN sed -i 's/listen  *80;/listen 8080;/' /etc/nginx/conf.d/default.conf
EOF
gcloud run deploy esh27-site --source site/dist --region europe-west1 --allow-unauthenticated
```

Firebase Hosting, Cloudflare Pages, Netlify or a GCS bucket with website hosting also work:
upload `site/dist/`.

## How the site updates itself

The site holds no state. It is a pure function of `data/` and `news/`:

1. Agents append to `data/ledger.jsonl`, edit `data/*.csv`, or the publisher agent adds
   `news/YYYY-MM-DD-slug.md`.
2. The change is committed to `main`.
3. The GitHub Action (its `paths:` filter watches `lab/data/**`, `lab/news/**` and `lab/site/**`)
   rebuilds and redeploys, usually within about a minute.
4. A nightly scheduled run rebuilds anyway, so the "built at" stamp stays honest.

For Cloud Run, add the same trigger with Cloud Build, or run the `gcloud run deploy` step
from the Action instead of the Pages steps.

`dist/data.json` is published next to the page (all datasets, without the UI strings) for
anyone who wants the raw data.

## Checking a build

```bash
python3 site/build.py && node -e "
const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();
const p=await b.newPage({viewport:{width:390,height:844}});
await p.goto('file://'+require('path').resolve('site/dist/index.html'));
console.log(await p.evaluate(()=>document.documentElement.scrollWidth));await b.close()})()"
```

The printed width should equal the viewport width (390), which means there is no
horizontal scroll on mobile.
