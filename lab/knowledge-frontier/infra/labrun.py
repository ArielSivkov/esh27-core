#!/usr/bin/env python3
"""labrun: every lab run leaves a permanent, checkable record in git, successes and failures alike.

  labrun.py run --name NAME [--hypothesis TEXT --success TEXT --success-expr EXPR]
                [--collect PATH]... [--timeout S] [--no-push] -- COMMAND...
      1. writes runs/<id>/manifest.json with the hypothesis and success criterion and commits it
         BEFORE the command starts (pre-registration; pushed when a branch is available);
      2. runs the command, streaming its output to the screen and to runs/<id>/log.txt;
      3. records exit code, wall/CPU time, peak memory, machine, whitelisted env, output files with sha256;
         files over the size limit are not committed, only their size and sha256;
      4. redacts credentials and personal data in the record, regenerates JOURNAL.md, commits, pushes.
      The command can write directly to $LAB_RUN_OUT; outputs/summary.json is lifted into the manifest.
  labrun.py checkpoint -m MSG [--import SRC[:DEST]]...   end-of-session save of code, logs and small files
  labrun.py gather [--no-push]   union run records from every remote branch into this branch
  labrun.py sync                 push commits that could not be pushed earlier
  labrun.py index                rebuild JOURNAL.md from runs/*/manifest.json
  labrun.py status               branch, push target, pending pushes, last runs

Push rules: the target is $LAB_BRANCH, else the current branch. main/master and the other names in
infra/lab.json "protected_branches" are refused. Never force-pushes. If the remote moved, rebases on it
(JOURNAL.md conflicts are resolved by regenerating it); anything else is left as a pending push.
"""
import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
RUNS = os.path.join(LAB, "runs")
JOURNAL = os.path.join(LAB, "JOURNAL.md")
CFG = json.load(open(os.path.join(HERE, "lab.json"), encoding="utf-8"))
sys.path.insert(0, HERE)
import secretscan  # noqa: E402


class LabError(Exception):
    pass


# ---------------------------------------------------------------- git helpers
_ROOT = []


def repo_root():
    if not _ROOT:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=LAB, capture_output=True, text=True)
        if p.returncode != 0:
            raise LabError("not inside a git checkout: " + p.stderr.strip()[:200])
        _ROOT.append(p.stdout.strip())
    return _ROOT[0]


def git(*args, check=True, timeout=None, env=None):
    # always from the repository root, so the repo-relative paths produced by rel() resolve correctly
    p = subprocess.run(["git", *args], cwd=repo_root(), capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, **(env or {})})
    if check and p.returncode != 0:
        raise LabError(f"git {' '.join(args[:2])} failed: {scrub(p.stderr.strip())[:500]}")
    return p


def rel(path):
    return os.path.relpath(os.path.abspath(path), repo_root())


def scrub(text):
    return secretscan.redact(text, secretscan.find(text))


def current_branch():
    return git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def is_protected(branch):
    b = branch.strip().split("/")[-1].lower() if branch.startswith("refs/") else branch.strip().lower()
    return b in {x.lower() for x in CFG["protected_branches"]} or b.startswith("release")


def push_target():
    b = os.environ.get("LAB_BRANCH") or current_branch()
    if not b or b == "HEAD":
        return None
    if is_protected(b):
        raise LabError(f"refusing to push to protected branch '{b}' (lab rule: never main)")
    return b


def pending_file():
    return os.path.join(git("rev-parse", "--absolute-git-dir").stdout.strip(), "labrun-pending.json")


def set_pending(reason):
    with open(pending_file(), "w", encoding="utf-8") as f:
        json.dump(dict(since=now(), reason=scrub(reason)[:800]), f)


def clear_pending():
    if os.path.exists(pending_file()):
        os.remove(pending_file())


def trailer():
    t = os.environ.get("LAB_COMMIT_TRAILER", "").strip()
    return ("\n\n" + t) if t else ""


def commit(paths, message):
    paths = [rel(p) for p in paths if os.path.exists(p)]
    if not paths:
        return False
    git("add", "--", *paths)
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return False
    msg = message + trailer()
    if secretscan.find(msg):
        raise LabError("commit message contains a credential or personal detail; not committing")
    p = git("commit", "-q", "-m", msg, check=False)
    if p.returncode != 0:
        git("reset", "-q", "--", *paths, check=False)
        raise LabError("commit refused (hook or git): " + scrub((p.stdout + p.stderr).strip())[:800])
    return True


def _rebase_onto(remote_ref):
    p = git("rebase", remote_ref, check=False, env={"GIT_EDITOR": "true"})
    for _ in range(50):
        if p.returncode == 0:
            return True
        conflicted = git("diff", "--name-only", "--diff-filter=U", check=False).stdout.split()
        journal = rel(JOURNAL)
        if conflicted and set(conflicted) <= {journal}:
            write_journal()
            git("add", "--", journal)
            p = git("rebase", "--continue", check=False, env={"GIT_EDITOR": "true"})
            continue
        break
    git("rebase", "--abort", check=False)
    return False


def push(what="", quiet=False):
    """Push HEAD to the lab branch. Returns True on success; on failure the push is left pending."""
    try:
        branch = push_target()
    except LabError as e:
        set_pending(str(e))
        print(f"labrun: {e}", file=sys.stderr)
        return False
    if os.environ.get("LAB_NO_PUSH"):
        set_pending("pushing disabled by LAB_NO_PUSH")
        return False
    if not branch:
        set_pending("no branch to push to (detached HEAD and LAB_BRANCH unset)")
        return False
    remote = CFG["remote"]
    last = ""
    for attempt in range(3):
        try:
            p = git("push", remote, f"HEAD:refs/heads/{branch}", check=False, timeout=CFG["push_timeout_s"])
        except subprocess.TimeoutExpired:
            last = "push timed out"
            continue
        if p.returncode == 0:
            clear_pending()
            if not quiet:
                print(f"labrun: pushed {what} to {remote}/{branch}")
            return True
        last = p.stderr.strip()
        if re.search(r"non-fast-forward|fetch first|rejected", last):
            f = git("fetch", "-q", remote, f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}", check=False)
            if f.returncode != 0:
                break
            if git("merge-base", "HEAD", f"refs/remotes/{remote}/{branch}", check=False).returncode != 0:
                git("fetch", "-q", "--deepen=200", remote, branch, check=False)
            if not _rebase_onto(f"refs/remotes/{remote}/{branch}"):
                last = "remote branch moved and the rebase had conflicts outside JOURNAL.md"
                break
            continue
        break
    set_pending(f"push to {remote}/{branch} failed: {last}")
    print(f"labrun: push failed, kept locally as pending ({scrub(last)[:300]})", file=sys.stderr)
    return False


def has_pending():
    return os.path.exists(pending_file())


# ---------------------------------------------------------------- records
def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def machine():
    mem = None
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal:"):
                mem = round(int(line.split()[1]) / 1048576, 1)
    except OSError:
        pass
    gpu = "none"
    if shutil.which("nvidia-smi"):
        q = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True)
        gpu = ", ".join(x.strip() for x in q.stdout.splitlines() if x.strip()) or "unknown"
    return dict(python=platform.python_version(), platform=platform.platform(), cpus=os.cpu_count(), mem_gb=mem, gpu=gpu)


def git_state():
    st = git("status", "--porcelain", "--untracked-files=no", check=False).stdout
    return dict(commit=git("rev-parse", "HEAD").stdout.strip(), branch=current_branch(),
                modified_tracked_files=len([x for x in st.splitlines() if x.strip()]))


def env_whitelist():
    return {k: os.environ[k] for k in CFG["env_whitelist"] if k in os.environ}


def ignored(relpath):
    return any(fnmatch.fnmatch(relpath, g) or fnmatch.fnmatch(os.path.basename(relpath), g) for g in CFG["ignore_globs"])


def copy_tree(src, dst_dir, limit_bytes, base_label):
    """Copy files from src (file or dir) into dst_dir. Returns (copied, skipped) entry lists."""
    copied, skipped = [], []
    src = os.path.abspath(src)
    items = []
    if os.path.isdir(src):
        for root, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in secretscan.SKIP_DIRS)
            for f in sorted(files):
                items.append((os.path.join(root, f), os.path.relpath(os.path.join(root, f), src)))
    elif os.path.isfile(src):
        items.append((src, os.path.basename(src)))
    for path, r in items:
        if os.path.islink(path):
            continue
        size = os.path.getsize(path)
        label = os.path.join(base_label, r)
        if ignored(r):
            skipped.append(dict(path=label, bytes=size, reason="ignored type"))
            continue
        if size > limit_bytes:
            skipped.append(dict(path=label, bytes=size, sha256=sha256_file(path), reason=f"over {limit_bytes >> 20} MB"))
            continue
        out = os.path.join(dst_dir, r)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(path, out)
        copied.append(out)
    return copied, skipped


def file_list(run_dir, subdir="outputs"):
    base = os.path.join(run_dir, subdir)
    out = []
    for root, _, files in os.walk(base):
        for f in sorted(files):
            p = os.path.join(root, f)
            out.append(dict(path=os.path.relpath(p, run_dir), bytes=os.path.getsize(p), sha256=sha256_file(p)))
    return sorted(out, key=lambda x: x["path"])


def new_run_id(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "run"
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{slug}-{secrets.token_hex(2)}"


def load_manifests():
    out = []
    if os.path.isdir(RUNS):
        for d in sorted(os.listdir(RUNS)):
            m = os.path.join(RUNS, d, "manifest.json")
            if os.path.isfile(m):
                try:
                    out.append(json.load(open(m, encoding="utf-8")))
                except ValueError:
                    out.append(dict(run_id=d, status="corrupt-manifest"))
    return out


def _cell(text, n=70):
    text = re.sub(r"\s+", " ", str(text or "")).replace("|", "/").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def write_journal():
    rows = load_manifests()
    lines = ["# יומן ריצות – נוצר אוטומטית", "",
             "הקובץ נבנה מחדש מ-`runs/*/manifest.json` בכל ריצה (`infra/labrun.py index`). לא לערוך ידנית.",
             "כל ריצה נרשמת, גם כישלון. ההשערה והקריטריון נשמרים בקומיט נפרד לפני שהריצה מתחילה.", "",
             "| התחלה (UTC) | ריצה | מצב | משך | עמידה בקריטריון | השערה | תוצאה |",
             "|---|---|---|---|---|---|---|"]
    for m in sorted(rows, key=lambda r: r.get("started_utc") or r.get("registered_utc") or ""):
        wall = m.get("wall_s")
        lines.append("| {} | `{}` | {} | {} | {} | {} | {} |".format(
            m.get("started_utc") or m.get("registered_utc") or "", m.get("run_id", ""), m.get("status", ""),
            f"{wall:.1f}s" if isinstance(wall, (int, float)) else "", m.get("verdict") or "",
            _cell(m.get("hypothesis")), _cell((m.get("summary") or {}).get("headline") if isinstance(m.get("summary"), dict) else "")))
    with open(JOURNAL, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- commands
def cmd_run(a):
    if not a.cmd:
        raise LabError("no command given (use: labrun.py run --name N -- command ...)")
    cmd = a.cmd[1:] if a.cmd[0] == "--" else a.cmd
    cwd = os.path.abspath(a.cwd or os.getcwd())
    rid = new_run_id(a.name)
    rdir = os.path.join(RUNS, rid)
    os.makedirs(os.path.join(rdir, "outputs"))
    man = dict(schema=1, run_id=rid, name=a.name, hypothesis=a.hypothesis, success_criterion=a.success,
               success_expr=a.success_expr, command=cmd, cwd=rel(cwd), registered_utc=now(), status="registered",
               git=git_state(), machine=machine(), env=env_whitelist())
    for key in ("hypothesis", "success_criterion", "name"):
        if man[key] and secretscan.find(man[key]):
            raise LabError(f"{key} contains a credential or personal detail; refusing to record it")
    write_json(os.path.join(rdir, "manifest.json"), man)
    committed = pushed_pre = False
    if not a.no_commit:
        committed = commit([os.path.join(rdir, "manifest.json")], f"run {rid}: registered")
        pushed_pre = (not a.no_push) and push("pre-registration", quiet=True)
    man["preregistration"] = dict(committed=committed, pushed=pushed_pre,
                                  commit=git("rev-parse", "HEAD").stdout.strip() if committed else None)

    env = {**os.environ, "LAB_RUN_ID": rid, "LAB_RUN_OUT": os.path.join(rdir, "outputs")}
    status, rc, ru, timed_out, finished = "ok", None, None, threading.Event(), threading.Event()
    log = open(os.path.join(rdir, "log.txt"), "w", encoding="utf-8", errors="replace")
    started = time.time()
    man["started_utc"] = now()
    proc = None
    old_handlers = {}

    def stop_child(*_):
        # never poll() here: reaping belongs to os.wait4 below, so the child's own resource usage is kept
        if proc is not None and not finished.is_set():
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace", bufsize=1, start_new_session=True)
        for sig in (signal.SIGINT, signal.SIGTERM):
            old_handlers[sig] = signal.signal(sig, lambda s, f: (man.update(status="interrupted"), stop_child()))
        timer = None
        if a.timeout:
            timer = threading.Timer(a.timeout, lambda: (timed_out.set(), stop_child()))
            timer.daemon = True
            timer.start()
        for line in proc.stdout:
            if not a.quiet:
                sys.stdout.write(line)
                sys.stdout.flush()
            log.write(line)
        _, wstatus, ru = os.wait4(proc.pid, 0)
        finished.set()
        rc = os.waitstatus_to_exitcode(wstatus)
        proc.returncode = rc
        if timer:
            timer.cancel()
        if timed_out.is_set():
            status = "timeout"
        elif man.get("status") == "interrupted":
            status = "interrupted"
        elif rc != 0:
            status = "failed"
    except FileNotFoundError as e:
        status, rc = "launch-error", 127
        log.write(f"labrun: could not start command: {e}\n")
    finally:
        log.close()
        for sig, h in old_handlers.items():
            signal.signal(sig, h)

    man.update(status=status, exit_code=rc, ended_utc=now(), wall_s=round(time.time() - started, 3))
    if ru is not None:
        man.update(cpu_user_s=round(ru.ru_utime, 3), cpu_sys_s=round(ru.ru_stime, 3), max_rss_mb=round(ru.ru_maxrss / 1024, 1))

    limit = int(CFG["max_file_mb"] * 1024 * 1024)
    out_root = os.path.join(rdir, "outputs")
    skipped = []
    for c in a.collect or []:
        src = os.path.join(cwd, c)
        if not os.path.exists(src):
            skipped.append(dict(path=c, reason="missing after run"))
            continue
        dst = out_root if os.path.isfile(src) else os.path.join(out_root, os.path.basename(os.path.normpath(c)))
        _, s = copy_tree(src, dst, limit, c)
        skipped += s
    # anything the command wrote into $LAB_RUN_OUT that is over the limit is moved out of the record;
    # the whole record is capped too (largest files go first), so one run cannot bloat the repo
    files = []
    for root, _, fs in os.walk(out_root):
        files += [os.path.join(root, f) for f in fs]
    total = 0
    for p in sorted(files, key=os.path.getsize):
        size = os.path.getsize(p)
        if size > limit or ignored(os.path.relpath(p, out_root)) or total + size > CFG.get("max_run_mb", 50) * 1048576:
            skipped.append(dict(path=os.path.relpath(p, rdir), bytes=size, sha256=sha256_file(p),
                                reason="over size limit, run cap, or ignored type"))
            os.remove(p)
        else:
            total += size
    allow = secretscan._load_allow()
    findings, _ = secretscan.scan_paths([out_root, os.path.join(rdir, "log.txt")], allow, do_redact=True)
    withheld = []
    for f in findings:
        if f["binary"] and os.path.exists(f["file"]):
            os.remove(f["file"])
            withheld.append(os.path.relpath(f["file"], rdir))
    man["redactions"] = [dict(file=os.path.relpath(f["file"], rdir), line=f["line"], kind=f["kind"]) for f in findings]
    man["withheld_binary_files"] = sorted(set(withheld))
    man["outputs"] = file_list(rdir)
    man["not_committed"] = skipped
    man["log"] = dict(bytes=os.path.getsize(os.path.join(rdir, "log.txt")), sha256=sha256_file(os.path.join(rdir, "log.txt")))
    summ = os.path.join(rdir, "outputs", "summary.json")
    if os.path.exists(summ) and os.path.getsize(summ) < 200_000:
        try:
            man["summary"] = json.load(open(summ, encoding="utf-8"))
        except ValueError as e:
            man["summary"] = dict(error=f"summary.json is not valid JSON: {e}")
    man["verdict"] = evaluate(a.success_expr, man) if a.success_expr else None
    man, n_fields = sanitize(man)
    if n_fields:
        man["redactions"].append(dict(file="manifest.json", line=0, kind=f"{n_fields} field(s)"))
    write_json(os.path.join(rdir, "manifest.json"), man)
    write_journal()
    if not a.no_commit:
        commit([rdir, JOURNAL], f"run {rid}: {status}" + (f", criterion {man['verdict']}" if man["verdict"] else "")
               + f" ({man['wall_s']:.1f}s)")
        if not a.no_push:
            push(f"run {rid}")
    print(f"labrun: {rid} {status} rc={rc} wall={man['wall_s']:.1f}s verdict={man['verdict']} -> {rel(rdir)}")
    return rc if isinstance(rc, int) else 1


def sanitize(obj):
    """Redact credentials/personal data in every string of a JSON-like object. Returns (clean, count)."""
    count = 0
    def walk(x):
        nonlocal count
        if isinstance(x, str):
            hits = secretscan.find(x)
            if hits:
                count += 1
                return secretscan.redact(x, hits)
            return x
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, dict):
            return {walk(k) if isinstance(k, str) else k: walk(v) for k, v in x.items()}
        return x
    return walk(obj), count


def evaluate(expr, man):
    """Evaluate a pre-registered success expression over the run record. Names: s (summary), rc, wall_s."""
    try:
        ok = eval(expr, {"__builtins__": {"len": len, "min": min, "max": max, "abs": abs, "all": all, "any": any}},
                  {"s": man.get("summary") or {}, "rc": man.get("exit_code"), "wall_s": man.get("wall_s")})
        return "pass" if ok else "fail"
    except Exception as e:  # a broken criterion is recorded, not hidden
        return f"error: {type(e).__name__}: {e}"[:200]


def cmd_checkpoint(a):
    limit = int(CFG["max_file_mb"] * 1024 * 1024)
    for spec in a.imports or []:
        src, _, dst = spec.partition(":")
        dst_dir = os.path.join(LAB, dst or os.path.basename(os.path.normpath(src)))
        copied, skipped = copy_tree(src, dst_dir, limit, "")
        big = [s for s in skipped if "sha256" in s]
        if big:
            ptr = os.path.join(dst_dir, "LARGE_FILES.json")
            old = json.load(open(ptr, encoding="utf-8")) if os.path.exists(ptr) else []
            byname = {x["path"]: x for x in old}
            for s in big:
                byname[s["path"]] = dict(s, recorded_utc=now())
            write_json(ptr, sorted(byname.values(), key=lambda x: x["path"]))
        print(f"labrun: imported {len(copied)} files from {src} into {rel(dst_dir)}; {len(big)} large files recorded by sha256 only")
    status = git("status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", "--", rel(LAB)).stdout
    changed = []
    for entry in status.split("\0"):
        if len(entry) > 3 and entry[:2].strip() != "D":
            changed.append(os.path.join(repo_root(), entry[3:]))
    findings, _ = secretscan.scan_paths([p for p in changed if os.path.isfile(p)], secretscan._load_allow())
    if findings:
        for f in findings:
            print(f"labrun: {f['category']} {f['kind']} in {rel(f['file'])} line {f['line']}", file=sys.stderr)
        raise LabError("checkpoint stopped: remove these before saving (values are not shown)")
    big = [p for p in changed if os.path.isfile(p) and os.path.getsize(p) > limit]
    if big:
        raise LabError("checkpoint stopped: files over the size limit: " + ", ".join(rel(p) for p in big))
    write_journal()
    git("add", "--ignore-removal", "--", rel(LAB))
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        print("labrun: nothing new to save")
        return 0 if not has_pending() else (0 if push("pending commits") else 1)
    msg = a.message + trailer()
    if secretscan.find(msg):
        raise LabError("commit message contains a credential or personal detail")
    p = git("commit", "-q", "-m", msg, check=False)
    if p.returncode != 0:
        raise LabError("commit refused: " + scrub((p.stdout + p.stderr).strip())[:800])
    print(f"labrun: checkpoint committed {git('rev-parse', '--short', 'HEAD').stdout.strip()}")
    return 0 if (a.no_push or push("checkpoint")) else 1


def cmd_gather(a):
    remote = CFG["remote"]
    git("fetch", "-q", "--depth=1", remote, f"+refs/heads/*:refs/remotes/{remote}/*", check=False, timeout=600)
    refs = [r for r in git("for-each-ref", "--format=%(refname)", f"refs/remotes/{remote}").stdout.split()
            if not r.endswith("/HEAD")]
    runs_rel = rel(RUNS)
    have = set(os.listdir(RUNS)) if os.path.isdir(RUNS) else set()
    added, sources = [], {}
    for ref in refs:
        ls = git("ls-tree", "-d", "--name-only", f"{ref}:{runs_rel}", check=False)
        if ls.returncode != 0:
            continue
        for rid in ls.stdout.split():
            if rid in have:
                continue
            git("checkout", ref, "--", f"{runs_rel}/{rid}")
            have.add(rid)
            added.append(rid)
            sources[ref.split("/", 3)[-1]] = sources.get(ref.split("/", 3)[-1], 0) + 1
    newest = None
    for ref in refs:
        if git("cat-file", "-e", f"{ref}:{rel(os.path.join(HERE, 'labrun.py'))}", check=False).returncode == 0:
            t = int(git("log", "-1", "--format=%ct", ref).stdout.strip() or 0)
            if not newest or t > newest[1]:
                newest = (ref.split("/", 3)[-1], t)
    print(f"labrun: gathered {len(added)} run records from {len(sources)} branches {sources}; "
          f"newest branch with lab tools: {newest[0] if newest else 'none'}")
    if added:
        write_journal()
        commit([RUNS, JOURNAL], f"gather: {len(added)} run records from {len(sources)} branches")
        if not a.no_push:
            push("gathered records")
    return 0


def cmd_sync(a):
    if not has_pending():
        print("labrun: nothing pending")
        return 0
    return 0 if push("pending commits") else 1


def cmd_index(a):
    write_journal()
    print(f"labrun: {rel(JOURNAL)} rebuilt from {len(load_manifests())} runs")
    return 0


def cmd_status(a):
    try:
        target = push_target()
    except LabError as e:
        target = f"refused ({e})"
    pend = json.load(open(pending_file())) if has_pending() else None
    runs = load_manifests()
    print(json.dumps(dict(branch=current_branch(), push_target=target, pending_push=pend, runs=len(runs),
                          last=[dict(run_id=m.get("run_id"), status=m.get("status"), verdict=m.get("verdict"))
                                for m in runs[-5:]]), ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="labrun.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--name", required=True)
    r.add_argument("--hypothesis", default="")
    r.add_argument("--success", default="", help="success criterion in words, fixed before the run")
    r.add_argument("--success-expr", default="", help="the same criterion as an expression over s (summary), rc, wall_s")
    r.add_argument("--collect", action="append", help="file or directory (relative to --cwd) to keep as output")
    r.add_argument("--cwd")
    r.add_argument("--timeout", type=float)
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--no-push", action="store_true")
    r.add_argument("--no-commit", action="store_true")
    r.add_argument("cmd", nargs=argparse.REMAINDER)
    c = sub.add_parser("checkpoint")
    c.add_argument("-m", "--message", required=True)
    c.add_argument("--import", dest="imports", action="append", metavar="SRC[:DEST]")
    c.add_argument("--no-push", action="store_true")
    g = sub.add_parser("gather")
    g.add_argument("--no-push", action="store_true")
    for name in ("sync", "index", "status"):
        sub.add_parser(name)
    a = ap.parse_args(argv)
    try:
        return dict(run=cmd_run, checkpoint=cmd_checkpoint, gather=cmd_gather, sync=cmd_sync,
                    index=cmd_index, status=cmd_status)[a.command](a)
    except LabError as e:
        print(f"labrun: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
