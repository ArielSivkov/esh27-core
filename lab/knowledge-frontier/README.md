# Knowledge Frontier Lab: persistent memory

**בקצרה (לאריאל):** כל ריצה נשמרת כאן אוטומטית: השערה וקריטריון לפני ההרצה, ואחריה התוצאה, הלוג והקוד, גם כשנכשלה. סקריפט אחד (`infra/bootstrap.sh`) בונה את המעבדה מחדש ממכונה ריקה ובודק שהכול שלם. מפתחות ופרטים אישיים נחסמים לפני שהם נכנסים לגיט.

This folder is the durable copy of work that ran in ephemeral cloud containers. It does not include the large data files; each one can be rebuilt from its source listed below.

## Start here (every session)
1. Rebuild and verify: `bash lab/knowledge-frontier/infra/bootstrap.sh` from an empty directory, or from anywhere
   `curl -fsSL https://raw.githubusercontent.com/ArielSivkov/esh27-core/<branch>/lab/knowledge-frontier/infra/bootstrap.sh | bash`.
   It clones every branch tip, picks the newest branch that holds `infra/labrun.py`, installs exact versions,
   installs the git hooks, gathers run records from all branches, probes the hosts and runs the offline checks
   of `infra/expected.json`. `LAB_DATA=1` also rebuilds the raw data from the Hugging Face mirrors (`infra/build_data.py`).
2. Read `JOURNAL.md` (every run, generated), `seal/arms_results.md`, and the Drive log.

## Every experiment goes through labrun
```
python3 lab/knowledge-frontier/infra/labrun.py run --name NAME \
    --hypothesis "what we expect" --success "criterion in words" --success-expr "s['mean'] >= 0.5" \
    [--collect PATH] [--timeout SECONDS] -- COMMAND ...
```
- The manifest with the hypothesis and the criterion is committed before the command starts (pre-registration).
- After the run: exit code, wall/CPU time, peak memory, machine, whitelisted env, outputs with sha256, the log,
  and the verdict against the criterion. A failure is recorded exactly like a success. The command may write to
  `$LAB_RUN_OUT`; `outputs/summary.json` (with a `headline`) is lifted into the manifest and `JOURNAL.md`.
- Files over 5 MB are not committed: their size and sha256 are recorded so a rebuild can be checked.
- Push target: `$LAB_BRANCH`, else the current branch. `main`/`master` are refused by the code. No force pushes.
  If the remote moved, labrun rebases on it. If pushing is not possible, commits stay local and
  `labrun.py sync` pushes them later.

## End of every session
`python3 lab/knowledge-frontier/infra/labrun.py checkpoint -m "what this session did" --import <scratch dir>:<dest>`
copies code and small outputs from a scratch directory into the lab, records large files by sha256 only,
scans everything, commits and pushes.

## Rules enforced by code, not by memory
- `infra/secretscan.py` runs as pre-commit and commit-msg hooks and inside labrun: credentials (GitHub, Hugging Face,
  Kaggle, Anthropic, OpenAI, Google, AWS, Slack, Telegram, private keys, URL passwords, random-looking `key = "..."`)
  and personal data (Israeli phone numbers, e-mail addresses) are redacted in run records and block manual commits.
  A matched value is never printed. The repository is public: everything committed here is public.
- `infra/hosts.py` names every blocked host; `infra/build_data.py` refuses to run when its source is blocked.
- `infra/verify.py` fails loudly; a skipped check is never counted as a pass.
- Tests: `python3 -I infra/tests/test_secretscan.py` and `python3 -I infra/tests/test_labrun.py`
  (the second runs full push/rebase/hook scenarios against a local bare repository).

## topo/: topology of human knowledge
- The research log, with dated entries and corrections, is in a Google Drive doc: "🕸️ טופולוגיית הידע האנושי – יומן מחקר".
- Data sources, rebuilt on demand (`infra/build_data.py`, gated by `infra/verify.py --data`):
  - arXiv metadata: HF `librarian-bots/arxiv-metadata-snapshot` (read with `id` and `categories`) and HF `gfissore/arxiv-abstracts-2021`.
  - Daily arXiv refresh: `refresh_daily.py`, which pulls `export.arxiv.org/rss/<cat>`.
  - OpenAlex mirror: HF `Mearman/OpenAlex`. Its `works/topics` table holds subfield ids, and its concept tags are noisy (log entry 8).
- Main method: `ipf.py`. It builds a symmetric max-entropy null over the 2×2×2 table and estimates the expected number of papers in all three fields, given all three pairwise counts.
- `post2021.py` compares the periods up to 2021 and 2022–2026.

## seal/: verifier-gated self-training
- `loop_sci_param.py` runs the loop on CPU; `loop_sci_gpu.py` and `loop_sci_gpu2.py` run on Kaggle GPU.
- `frozen_sets_sci.json` is the frozen evaluation set. Never train on it. `infra/verify.py` regenerates it from
  seed 27 with the committed code and checks it is byte-identical (also `frozen_sets.json` from `loop.py`).
- `arms_results.md` holds the results of every run, CPU and Kaggle T4. `infra/cost_report.py` derives speed and
  cost per experiment from it, tying every number to a verbatim line.
- Kaggle runs are driven through `api.kaggle.com/v1/kernels.KernelsApiService/{SaveKernel,GetKernelSessionStatus,ListKernelSessionOutput}`. The credential is injected by the environment proxy and is never stored here.
