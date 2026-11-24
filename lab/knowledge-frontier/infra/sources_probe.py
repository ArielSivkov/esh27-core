#!/usr/bin/env python3
"""Probe free data and compute sources that this machine reaches WITHOUT new network approvals, and measure them.

Everything is fetched with plain git reads into data/sources/ (ignored by git). Nothing from those repositories is
executed: they are read as data only (yaml.safe_load, file listings). Writes to $LAB_RUN_OUT (or ./probe_out):
  summary.json                    counts, timings, what is reachable and what is not
  targets_erdos_open_oeis.json    open Erdős problems that cite OEIS sequences, with whether a Lean statement exists

Sources (all public):
  OEIS data       github.com/oeis/oeisdata           (oeis.org itself is blocked here; content CC BY-SA 4.0)
  Erdős problems  github.com/teorth/erdosproblems    (erdosproblems.com is blocked here; Apache-2.0)
  Lean statements github.com/google-deepmind/formal-conjectures (Apache-2.0)
  Lean toolchain  github.com/leanprover/lean4 releases (download path only; installing needs a separate approval)
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
SRC = os.path.join(LAB, "data", "sources")
OUT = os.environ.get("LAB_RUN_OUT") or os.path.join(os.getcwd(), "probe_out")
os.makedirs(SRC, exist_ok=True)
os.makedirs(OUT, exist_ok=True)


def git(*args, cwd=None, timeout=600):
    t = time.time()
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p, round(time.time() - t, 2)


def clone(url, name, *extra):
    dest = os.path.join(SRC, name)
    if os.path.isdir(os.path.join(dest, ".git")):
        p, s = git("fetch", "-q", "--depth", "1", "origin", cwd=dest)
        return dest, s, p.returncode == 0, "updated"
    p, s = git("clone", "-q", "--depth", "1", *extra, url, dest)
    return dest, s, p.returncode == 0, (p.stderr.strip().splitlines() or [""])[-1][:200]


def main():
    summary = dict(sources={})
    # 1. Erdős problems
    dest, secs, ok, note = clone("https://github.com/teorth/erdosproblems", "erdosproblems")
    import yaml
    problems = yaml.safe_load(open(os.path.join(dest, "data", "problems.yaml"), encoding="utf-8")) if ok else []
    rev = git("rev-parse", "HEAD", cwd=dest)[0].stdout.strip() if ok else None
    status = {}
    for p in problems:
        s = str(p.get("status", {}).get("state") if isinstance(p.get("status"), dict) else p.get("status"))
        status[s] = status.get(s, 0) + 1
    def oeis_ids(p):
        return [x for x in (p.get("oeis") or []) if isinstance(x, str) and re.fullmatch(r"A\d{6}", x)]
    open_oeis = [p for p in problems if "open" in str(p.get("status")).lower() and oeis_ids(p)]
    summary["sources"]["erdosproblems"] = dict(reachable=ok, clone_s=secs, revision=rev, problems=len(problems),
                                               status=dict(sorted(status.items(), key=lambda kv: -kv[1])),
                                               open_with_oeis=len(open_oeis), note=note)
    # 2. Lean statements of the problems
    dest2, secs2, ok2, note2 = clone("https://github.com/google-deepmind/formal-conjectures", "formal-conjectures",
                                     "--filter=blob:none", "--no-checkout")
    lean_numbers = set()
    if ok2:
        files = git("ls-tree", "-r", "--name-only", "HEAD", cwd=dest2)[0].stdout.splitlines()
        erdos_files = [f for f in files if re.search(r"ErdosProblems/\d+\.lean$", f)]
        lean_numbers = {re.search(r"(\d+)\.lean$", f).group(1) for f in erdos_files}
        summary["sources"]["formal-conjectures"] = dict(reachable=True, clone_s=secs2, lean_files=len([f for f in files if f.endswith(".lean")]),
                                                        erdos_problem_files=len(erdos_files),
                                                        revision=git("rev-parse", "HEAD", cwd=dest2)[0].stdout.strip())
    else:
        summary["sources"]["formal-conjectures"] = dict(reachable=False, note=note2)
    # 3. OEIS data: partial clone, then fetch only the sequences the open problems cite
    dest3, secs3, ok3, note3 = clone("https://github.com/oeis/oeisdata", "oeisdata", "--filter=blob:none", "--no-checkout")
    fetched, fetch_s, n_seq = [], None, None
    if ok3:
        tree = git("ls-tree", "-r", "--name-only", "HEAD", cwd=dest3)[0].stdout.splitlines()
        n_seq = sum(1 for f in tree if f.startswith("seq/") and f.endswith(".seq"))
        wanted = sorted({a for p in open_oeis for a in oeis_ids(p)})
        paths = [f"seq/{a[:4]}/{a}.seq" for a in wanted]
        have = set(tree)
        paths = [x for x in paths if x in have]
        t = time.time()
        git("sparse-checkout", "set", "--no-cone", *paths, cwd=dest3)
        p, _ = git("checkout", "-q", cwd=dest3, timeout=1200)
        fetch_s = round(time.time() - t, 2)
        fetched = [x for x in paths if os.path.exists(os.path.join(dest3, x))]
        summary["sources"]["oeisdata"] = dict(reachable=True, clone_s=secs3, sequences_in_tree=n_seq,
                                              cited_by_open_problems=len(wanted), fetched=len(fetched), fetch_s=fetch_s,
                                              revision=git("rev-parse", "HEAD", cwd=dest3)[0].stdout.strip())
    else:
        summary["sources"]["oeisdata"] = dict(reachable=False, note=note3)
    # 4. Lean toolchain download path (no download, no install)
    url = "https://github.com/leanprover/lean4/releases/download/v4.20.0/lean-4.20.0-linux.tar.zst"

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, method="HEAD"), timeout=20)
        lean = dict(download_path="no redirect")
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location", "")
        lean = dict(http=e.code, redirect_host=urllib.parse.urlparse(loc).netloc if loc else None)
    except Exception as e:
        lean = dict(error=f"{type(e).__name__}: {e}"[:160])
    lean["installed"] = False
    lean["note"] = "installing means running downloaded binaries; not done without Ariel's explicit approval"
    summary["sources"]["lean-toolchain"] = lean
    # targets: open Erdős problems citing OEIS, with Lean-statement availability and local sequence files
    targets = []
    for p in open_oeis:
        num = str(p.get("number"))
        ids = oeis_ids(p)
        targets.append(dict(problem=num, oeis=ids, lean_statement=num in lean_numbers, prize=p.get("prize"),
                            tags=p.get("tags"), sequences_local=[a for a in ids if f"seq/{a[:4]}/{a}.seq" in fetched]))
    with_lean = sum(t["lean_statement"] for t in targets)
    json.dump(dict(source="teorth/erdosproblems (Apache-2.0) + google-deepmind/formal-conjectures (Apache-2.0) "
                          "+ oeis/oeisdata (CC BY-SA 4.0)", revision=rev, targets=targets),
              open(os.path.join(OUT, "targets_erdos_open_oeis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    summary["targets"] = dict(open_with_oeis=len(targets), with_lean_statement=with_lean)
    summary["headline"] = (f"OEIS {n_seq} sequences via GitHub; Erdős {len(problems)} problems, "
                           f"{status.get('open', 0)} open, {len(targets)} open citing OEIS, {with_lean} of them with a Lean statement; "
                           f"Lean download path {'open' if lean.get('redirect_host') else 'closed'}, not installed")
    json.dump(summary, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1)[:3000])
    return 0 if ok and ok2 and ok3 else 1


if __name__ == "__main__":
    import urllib.error
    import urllib.parse
    sys.exit(main())
