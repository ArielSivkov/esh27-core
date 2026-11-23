# Knowledge Frontier Lab: persistent memory

This folder is the durable copy of work that ran in an ephemeral cloud container. It does not include the large data files; each one can be rebuilt from its source listed below.

## topo/: topology of human knowledge
- The research log, with dated entries and corrections, is in a Google Drive doc: "🕸️ טופולוגיית הידע האנושי – יומן מחקר".
- Data sources, rebuilt on demand:
  - arXiv metadata: HF `librarian-bots/arxiv-metadata-snapshot` (read with `id` and `categories`) and HF `gfissore/arxiv-abstracts-2021`.
  - Daily arXiv refresh: `refresh_daily.py`, which pulls `export.arxiv.org/rss/<cat>`.
  - OpenAlex mirror: HF `Mearman/OpenAlex`. Its `works/topics` table holds subfield ids, and its concept tags are noisy (log entry 8).
- Main method: `ipf.py`. It builds a symmetric max-entropy null over the 2×2×2 table and estimates the expected number of papers in all three fields, given all three pairwise counts.
- `post2021.py` compares the periods up to 2021 and 2022–2026.

## seal/: verifier-gated self-training
- `loop_sci_param.py` runs the loop on CPU; `loop_sci_gpu.py` and `loop_sci_gpu2.py` run on Kaggle GPU.
- `frozen_sets_sci.json` is the frozen evaluation set. Never train on it.
- `arms_results.md` holds the results of every run, CPU and Kaggle T4.
- Kaggle runs are driven through `api.kaggle.com/v1/kernels.KernelsApiService/{SaveKernel,GetKernelSessionStatus,ListKernelSessionOutput}`. The credential is injected by the environment proxy and is never stored here.
