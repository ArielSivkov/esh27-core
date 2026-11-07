# S27 News: article format

Every article is one Markdown file in this folder. The site build (`site/build.py`) picks them
up automatically and shows them in the progress log ("יומן התקדמות"). `README.md` is ignored.

## File name

```
YYYY-MM-DD-short-slug.md      e.g. 2026-11-04-launch.md
```

## Front matter

The file opens with a YAML-style block. Keep it flat: one `key: value` per line, and lists in
`[a, b, c]` form. The build uses a small parser, not full YAML.

```yaml
---
title: "כותרת הכתבה"
date: 2026-11-04
lang: he                 # he | en
tags: [השקה, Lean 4, G017]
claim_level: none        # none | L0 | L1 | L2 | L3 | L4
author: S27 News         # optional
summary: "One or two sentences for the card. Optional; defaults to the first paragraph."
draft: false             # optional; true = not published
---
```

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | Headline. |
| `date` | yes | Publication date, ISO `YYYY-MM-DD`. Articles are sorted by it, newest first. |
| `lang` | yes | `he` or `en`. Sets the text direction of the article. |
| `tags` | yes | Topics, goal IDs (`G017`), tool names. |
| `claim_level` | yes | The **strongest** mathematical claim the article makes. |
| `summary` | no | The excerpt on the card. |
| `draft` | no | `true` keeps the article out of the build. |

## Claim level: the rule

`claim_level` is the highest claim level of any result the article reports, as recorded in
`data/ledger.jsonl`:

- `none`: the article makes no mathematical claim (announcements, explainers, interviews).
- `L0` idea, `L1` numerical evidence, `L2` informal proof (checked by a second agent or a human).
- `L3` machine-verified (clean `lake build`, a checked DRAT proof, or an exact check of an
  approved statement). Use it only if the ledger entry has `certificate.verified: true`, and link
  the certificate in the text.
- `L4`: L3 plus external review, publication, or a merge into Mathlib.

Words such as "הוכחנו", "proved" or "solved" may appear only in L3 and L4 articles. An L3 result
on part of a problem (a special case, an improved bound) is described as exactly that.

## Body

Markdown subset supported by the build: `#`–`####` headings, paragraphs, `-` and `1.` lists,
`>` quotes, `---` rules, `**bold**`, `*italic*`, `` `code` ``, `[links](https://…)`, and math in
`$…$` or `$$…$$` (rendered with KaTeX). Raw HTML is escaped. Tables and images are not supported.
A leading `# Title` that repeats the title is dropped.

Style: inspiring but sober. Say what was tried, what worked, what failed, and what the claim
level is. Cite sources. Never round a result up.
