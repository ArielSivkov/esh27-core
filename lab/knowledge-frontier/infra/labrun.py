#!/usr/bin/env python3
"""labrun: every lab run leaves a permanent, checkable record in git, successes and failures alike.

  labrun.py run --name NAME [--hypothesis TEXT --success TEXT --success-expr EXPR]
                [--collect PATH]... [--timeout S] [--no-push] -- COMMAND...
      1. writes runs/<id>/manifest.json with the hypothesis and success criterion and commits it
         BEFORE the command starts (pre-registration; pushed when a branch is available);
      2. runs the command, streaming its output to the screen and to runs/<id>/log.txt
         (the committed log keeps the first and last 2 MB; the full log stays in data/, ignored by git);
      3. records exit code, wall/CPU time, peak memory, machine, whitelisted env, tracked files the command
         changed, and output files with sha256; files over the size limit are moved to data/ and recorded
         by size and sha256 only;
      4. redacts credentials and personal data in the record, regenerates JOURNAL.md, commits, pushes.
      The command can write to $LAB_RUN_OUT; outputs/summary.json is lifted into the manifest.
  labrun.py checkpoint -m MSG [--import SRC[:DEST]]...   end-of-session save of code, logs and small files
  labrun.py gather [--no-push]   union run records from every remote branch into this branch
  labrun.py recover [--no-push]  finalize runs whose labrun process died on this machine (status "lost")
  labrun.py sync                 push commits that could not be pushed earlier
  labrun.py index                rebuild JOURNAL.md from runs/*/manifest.json
  labrun.py status               branch, push target, pending pushes, active and last runs

Push rules: the target is $LAB_BRANCH, else the current branch. main/master, the other names in
infra/lab.json "protected_branches", and ref-like names (origin/..., heads/..., HEAD, @) are refused.
Never force-pushes. If the remote moved, rebases on it (JOURNAL.md conflicts are resolved by regenerating it).
A push is marked pending before it starts and cleared only after it succeeded.
Every commit of a run carries "manifest-sha256: <hex>" in its message, so verify.py can detect later edits.
"""
import argparse
import ast
import contextlib
import datetime as dt
import fcntl
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
DATA_RUNS = os.path.join(LAB, "data", "runs")
JOURNAL = os.path.join(LAB, "JOURNAL.md")
CFG = json.load(open(os.path.join(HERE, "lab.json"), encoding="utf-8"))
LOG_HEAD = int(CFG.get("log_head_mb", 2) * 1048576)
LOG_TAIL = int(CFG.get("log_tail_mb", 2) * 1048576)
LOG_LOCAL_MAX = int(CFG.get("log_local_max_mb", 500) * 1048576)
FINAL_STATES = {"ok", "failed", "timeout", "interrupted", "launch-error", "lost"}
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


def git_dir():
    return git("rev-parse", "--absolute-git-dir").stdout.strip()


def rel(path):
    return os.path.relpath(os.path.abspath(path), repo_root())


def scrub(text):
    return secretscan.safe(text)


def current_branch():
    return git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


@contextlib.contextmanager
def git_lock():
    """Serialize the git steps of parallel labrun processes in one checkout (commands still run in parallel)."""
    with open(os.path.join(git_dir(), "labrun.lock"), "w") as fh:
        deadline = time.time() + 900
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() > deadline:
                    raise LabError("another labrun held the git lock for 15 minutes")
                time.sleep(0.2)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def ensure_hooks():
    want = f"{rel(LAB)}/infra/hooks"
    have = git("config", "--get", "core.hooksPath", check=False).stdout.strip()
    if not have:
        git("config", "core.hooksPath", want)
        print(f"labrun: installed the lab git hooks (core.hooksPath={want})", file=sys.stderr)
    elif have.rstrip("/") != want:
        print(f"labrun: warning: core.hooksPath is {have}, not the lab hooks; labrun still scans what it commits",
              file=sys.stderr)


BAD_COMPONENTS = {"head", "heads", "origin", "refs", "remotes", "@", "fetch_head", "orig_head"}


def validate_branch(b):
    b = b.strip()
    if b.startswith("refs/heads/"):
        b = b[len("refs/heads/"):]
    parts = [x.lower() for x in b.split("/")]
    protected = {x.lower() for x in CFG["protected_branches"]}
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", b) or ".." in b or "//" in b or b.endswith(("/", ".lock", ".")):
        raise LabError(f"refusing branch name {b!r} (not a plain branch name)")
    if any(x in BAD_COMPONENTS for x in parts):
        raise LabError(f"refusing branch name {b!r} (looks like a ref, not a branch)")
    if any(x in protected or x.startswith("release") for x in parts):
        raise LabError(f"refusing to push to protected branch '{b}' (lab rule: never main)")
    if git("check-ref-format", "--branch", b, check=False).returncode != 0:
        raise LabError(f"refusing branch name {b!r} (git rejects it)")
    return b


def push_target(stored=None):
    explicit = os.environ.get("LAB_BRANCH") or stored
    if explicit:  # anything configured is validated, "HEAD" included
        return validate_branch(explicit)
    b = current_branch()
    if not b or b == "HEAD":  # detached HEAD and nothing configured: commit locally, push later
        return None
    return validate_branch(b)


def pending_file():
    return os.path.join(git_dir(), "labrun-pending.json")


def read_pending():
    try:
        return json.load(open(pending_file(), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def set_pending(reason, branch=None):
    with open(pending_file(), "w", encoding="utf-8") as f:
        json.dump(dict(since=now(), reason=scrub(reason)[:800], branch=branch), f)


def clear_pending():
    if os.path.exists(pending_file()):
        os.remove(pending_file())


def has_pending():
    return os.path.exists(pending_file())


def trailer():
    t = os.environ.get("LAB_COMMIT_TRAILER", "").strip()
    return ("\n\n" + t) if t else ""


def commit(paths, message, hashes=()):
    """Commit exactly these paths (nothing else that may be staged). hashes: lines appended to the message."""
    paths = [rel(p) for p in paths if os.path.lexists(p)]
    if not paths:
        return False
    git("add", "--", *paths)
    if git("diff", "--cached", "--quiet", "--", *paths, check=False).returncode == 0:
        return False
    msg = message + ("\n\n" + "\n".join(hashes) if hashes else "") + trailer()
    if secretscan.find(msg):
        raise LabError("commit message contains a credential or personal detail; not committing")
    p = git("commit", "-q", "-m", msg, "--", *paths, check=False)
    if p.returncode != 0:
        git("reset", "-q", "--", *paths, check=False)
        raise LabError("commit refused (hook or git): " + scrub((p.stdout + p.stderr).strip())[:800])
    return True


def _rebase_onto(remote_ref):
    p = git("rebase", "--autostash", remote_ref, check=False, env={"GIT_EDITOR": "true"})
    conflicted = []
    for _ in range(50):
        if p.returncode == 0:
            return True, ""
        conflicted = git("diff", "--name-only", "--diff-filter=U", check=False).stdout.split()
        journal = rel(JOURNAL)
        if conflicted and set(conflicted) <= {journal}:
            write_journal()
            git("add", "--", journal)
            p = git("rebase", "--continue", check=False, env={"GIT_EDITOR": "true"})
            continue
        break
    reason = ("conflicts in " + ", ".join(conflicted[:5])) if conflicted else scrub(p.stderr.strip())[:300]
    git("rebase", "--abort", check=False)
    return False, reason


def push(what="", quiet=False, stored_branch=None):
    """Push HEAD to the lab branch. Marked pending before it starts; cleared only when it succeeded."""
    try:
        branch = push_target(stored_branch)
    except LabError as e:
        set_pending(str(e))
        print(f"labrun: {e}", file=sys.stderr)
        return False
    if not branch:
        set_pending("no branch to push to (detached HEAD and LAB_BRANCH unset)")
        return False
    set_pending(f"push of {what} started, not confirmed", branch)
    if os.environ.get("LAB_NO_PUSH"):
        set_pending("pushing disabled by LAB_NO_PUSH", branch)
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
                last = "fetch of the moved remote branch failed: " + f.stderr.strip()
                break
            if git("merge-base", "HEAD", f"refs/remotes/{remote}/{branch}", check=False).returncode != 0:
                git("fetch", "-q", "--deepen=200", remote, branch, check=False)
            ok, why = _rebase_onto(f"refs/remotes/{remote}/{branch}")
            if not ok:
                last = f"the remote branch moved and the rebase failed ({why})"
                break
            continue
        break
    set_pending(f"push to {remote}/{branch} failed: {last}", branch)
    print(f"labrun: push failed, kept locally as pending ({scrub(last)[:300]})", file=sys.stderr)
    return False


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


def manifest_line(rdir):
    return f"manifest-sha256: {sha256_file(os.path.join(rdir, 'manifest.json'))}"


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


def tracked_status():
    return set(x for x in git("status", "--porcelain", "--untracked-files=no", check=False).stdout.splitlines() if x.strip())


def git_state():
    return dict(commit=git("rev-parse", "HEAD").stdout.strip(), branch=current_branch(),
                modified_tracked_files=len(tracked_status()))


def env_whitelist():
    return {k: os.environ[k] for k in CFG["env_whitelist"] if k in os.environ}


def ignored(relpath):
    return any(fnmatch.fnmatch(relpath, g) or fnmatch.fnmatch(os.path.basename(relpath), g) for g in CFG["ignore_globs"])


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


def move_out(path, rid, rel_to):
    """Move a file out of the record into data/runs/<id>/ (ignored by git). Returns its new repo-relative path."""
    dest = os.path.join(DATA_RUNS, rid, os.path.relpath(path, rel_to))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(path, dest)
    return rel(dest)


def copy_tree(src, dst_dir, base_label):
    """Copy regular files from src (file or dir) into dst_dir; symlinks are recorded, never followed."""
    copied, skipped = [], []
    src = os.path.abspath(src)
    items = []
    if os.path.isdir(src) and not os.path.islink(src):
        for root, dirs, files in os.walk(src):
            dirs[:] = sorted(d for d in dirs if d not in {".git", ".venv"})
            for f in sorted(files):
                items.append((os.path.join(root, f), os.path.relpath(os.path.join(root, f), src)))
    elif os.path.lexists(src):
        items.append((src, os.path.basename(src)))
    for path, r in items:
        label = os.path.join(base_label, r)
        if os.path.islink(path) or not os.path.isfile(path):
            skipped.append(dict(path=label, reason="symlink or special file, not followed"))
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
            if os.path.isfile(p) and not os.path.islink(p):
                out.append(dict(path=os.path.relpath(p, run_dir), bytes=os.path.getsize(p), sha256=sha256_file(p)))
    return sorted(out, key=lambda x: x["path"])


def new_run_id(name):
    slug = re.sub(r"[^a-z0-9]+", "-", secretscan.safe(name).lower()).strip("-")[:40] or "run"
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
             "כל ריצה נרשמת, גם כישלון. ההשערה והקריטריון נשמרים בקומיט נפרד לפני שהריצה מתחילה;",
             "העמודה 'רישום מראש' אומרת אם הקומיט הזה גם נדחף לגיטהאב לפני ההרצה.", "",
             "| התחלה (UTC) | ריצה | מצב | משך | עמידה בקריטריון | רישום מראש | השערה | תוצאה |",
             "|---|---|---|---|---|---|---|---|"]
    for m in sorted(rows, key=lambda r: r.get("started_utc") or r.get("registered_utc") or ""):
        wall = m.get("wall_s")
        pre = m.get("preregistration") or {}
        pre_s = "נדחף" if pre.get("pushed") else ("קומיט מקומי" if pre.get("committed") else "")
        summ = m.get("summary") if isinstance(m.get("summary"), dict) else {}
        lines.append("| {} | `{}` | {} | {} | {} | {} | {} | {} |".format(
            m.get("started_utc") or m.get("registered_utc") or "", m.get("run_id", ""), m.get("status", ""),
            f"{wall:.1f}s" if isinstance(wall, (int, float)) else "", m.get("verdict") or "", pre_s,
            _cell(m.get("hypothesis")), _cell(summ.get("headline"))))
    with open(JOURNAL, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- process bookkeeping (for recover)
def _active_dir():
    d = os.path.join(git_dir(), "labrun-active")
    os.makedirs(d, exist_ok=True)
    return d


def _proc_start(pid):
    try:
        return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError, TypeError):
        return None


def _boot_id():
    try:
        return open("/proc/sys/kernel/random/boot_id").read().strip()
    except OSError:
        return None


def mark_active(rid, child=None):
    write_json(os.path.join(_active_dir(), rid + ".json"),
               dict(pid=os.getpid(), start=_proc_start(os.getpid()), boot=_boot_id(), since=now(),
                    child=child, child_start=_proc_start(child) if child else None))


def unmark_active(rid):
    p = os.path.join(_active_dir(), rid + ".json")
    if os.path.exists(p):
        os.remove(p)


def is_alive(entry):
    if entry.get("boot") != _boot_id() or entry.get("start") is None:
        return False
    return _proc_start(entry.get("pid")) == entry.get("start")


# ---------------------------------------------------------------- criterion
SAFE_FUNCS = {"len": len, "min": min, "max": max, "abs": abs, "all": all, "any": any, "round": round, "float": float}
SAFE_NODES = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd, ast.BinOp,
              ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Compare, ast.Eq, ast.NotEq, ast.Lt,
              ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.Constant, ast.Name, ast.Load,
              ast.Subscript, ast.Slice, ast.Tuple, ast.List, ast.Dict, ast.Call, ast.Attribute, ast.IfExp)


def check_expr(expr):
    """Reject anything but plain comparisons over s/rc/wall_s, whitelisted functions and dict .get()."""
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, SAFE_NODES):
            raise ValueError(f"not allowed in a criterion: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in {"s", "rc", "wall_s", *SAFE_FUNCS}:
            raise ValueError(f"unknown name in a criterion: {node.id}")
        if isinstance(node, ast.Attribute) and node.attr != "get":
            raise ValueError(f"attribute not allowed in a criterion: .{node.attr}")
        if isinstance(node, ast.Call) and not (
                (isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCS) or
                (isinstance(node.func, ast.Attribute) and node.func.attr == "get")):
            raise ValueError("only len/min/max/abs/all/any/round/float and .get() may be called in a criterion")
    return compile(tree, "<criterion>", "eval")


_EVAL_CHILD = r"""
import json, resource, sys
resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
sys.path.insert(0, sys.argv[1])
from labrun import check_expr, SAFE_FUNCS
d = json.load(sys.stdin)
ok = eval(check_expr(d["expr"]), {"__builtins__": {}, **SAFE_FUNCS}, {"s": d["s"], "rc": d["rc"], "wall_s": d["wall_s"]})
print("pass" if ok else "fail")
"""


def evaluate(expr, man):
    """Evaluate a pre-registered criterion in a separate process (10 s, 1 GB): it can neither hang nor escape."""
    try:
        check_expr(expr)
        p = subprocess.run([sys.executable, "-I", "-c", _EVAL_CHILD, HERE], capture_output=True, text=True, timeout=10,
                           input=json.dumps(dict(expr=expr, s=man.get("summary") or {}, rc=man.get("exit_code"),
                                                 wall_s=man.get("wall_s"))))
        if p.returncode != 0:
            return "error: " + ((p.stderr.strip().splitlines() or ["criterion failed"])[-1])[:180]
        return p.stdout.strip()
    except subprocess.TimeoutExpired:
        return "error: criterion took longer than 10 s"
    except Exception as e:  # a broken or refused criterion is recorded, not hidden
        return f"error: {type(e).__name__}: {e}"[:200]


# ---------------------------------------------------------------- run
class LogSink:
    """Committed log = first LOG_HEAD bytes + last LOG_TAIL bytes; the full stream is hashed and kept locally."""

    def __init__(self, path, full_path):
        self.f = open(path, "wb")
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        self.full = open(full_path, "wb")
        self.full_path = full_path
        self.h, self.total, self.head, self.tail, self.tail_len = hashlib.sha256(), 0, 0, [], 0
        self.lock = threading.Lock()

    def write(self, b):
        with self.lock:
            self.h.update(b)
            self.total += len(b)
            if self.total <= LOG_LOCAL_MAX:
                self.full.write(b)
                self.full.flush()
            if self.head < LOG_HEAD:
                take = b[: LOG_HEAD - self.head]
                self.f.write(take)
                self.f.flush()
                self.head += len(take)
                b = b[len(take):]
            if b:
                self.tail.append(b)
                self.tail_len += len(b)
                while self.tail and self.tail_len - len(self.tail[0]) >= LOG_TAIL:
                    self.tail_len -= len(self.tail.pop(0))

    def close(self):
        with self.lock:
            dropped = self.total - self.head - self.tail_len
            if self.tail:
                if dropped > 0:
                    self.f.write(f"\n[labrun: {dropped} bytes omitted here; sha256 of the full log is in the manifest, "
                                 f"a local copy is under data/]\n".encode())
                self.f.write(b"".join(self.tail))
            self.f.close()
            self.full.close()
            return dict(total_bytes=self.total, full_sha256=self.h.hexdigest(), omitted_bytes=max(dropped, 0),
                        local_copy=rel(self.full_path) + ("" if self.total <= LOG_LOCAL_MAX else " (truncated)"))


def cmd_run(a):
    if not a.cmd:
        raise LabError("no command given (use: labrun.py run --name N -- command ...)")
    cmd = a.cmd[1:] if a.cmd[0] == "--" else a.cmd
    if a.success_expr:  # a typo or a disallowed construct fails here, before anything is recorded or run
        try:
            check_expr(a.success_expr)
        except (SyntaxError, ValueError) as e:
            raise LabError(f"--success-expr refused before the run: {e}")
    for label, text in (("name", a.name), ("hypothesis", a.hypothesis), ("success", a.success)):
        if text and secretscan.find(text):
            raise LabError(f"--{label} contains a credential or personal detail; refusing to record it")
    if not a.no_push:
        push_target()  # an invalid or protected LAB_BRANCH fails before the run, not after it
    ensure_hooks()
    cwd = os.path.abspath(a.cwd or os.getcwd())
    rid = new_run_id(a.name)
    rdir = os.path.join(RUNS, rid)
    out_root = os.path.join(rdir, "outputs")
    os.makedirs(out_root)
    man = dict(schema=2, run_id=rid, name=a.name, hypothesis=a.hypothesis, success_criterion=a.success,
               success_expr=a.success_expr, command=cmd, cwd=rel(cwd), registered_utc=now(), status="registered",
               git=git_state(), machine=machine(), env=env_whitelist())
    man, _ = sanitize(man)  # a secret on the command line never reaches the registration commit
    write_json(os.path.join(rdir, "manifest.json"), man)
    mark_active(rid)
    committed = pushed_pre = False
    if not a.no_commit:
        with git_lock():
            committed = commit([os.path.join(rdir, "manifest.json")], f"run {rid}: registered", [manifest_line(rdir)])
            pushed_pre = (not a.no_push) and push("pre-registration", quiet=True)
    man["preregistration"] = dict(committed=committed, pushed=pushed_pre,
                                  commit=git("rev-parse", "HEAD").stdout.strip() if committed else None)

    before = tracked_status()
    env = {**os.environ, "LAB_RUN_ID": rid, "LAB_RUN_OUT": out_root}
    sink = LogSink(os.path.join(rdir, "log.txt"), os.path.join(DATA_RUNS, rid, "log.full.txt"))
    status, rc, ru = "ok", None, None
    flags = dict(timeout=False, interrupted=False, lingering=False)
    finished = threading.Event()
    proc = None
    grace = float(os.environ.get("LAB_KILL_GRACE_S", CFG.get("kill_grace_s", 10)))

    def kill_group(sig):
        if proc is not None and not finished.is_set():
            try:
                os.killpg(proc.pid, sig)
            except (ProcessLookupError, PermissionError):
                pass

    def stop(reason):
        flags[reason] = True
        kill_group(signal.SIGTERM)
        t = threading.Timer(grace, kill_group, (signal.SIGKILL,))  # a command that ignores SIGTERM is killed
        t.daemon = True
        t.start()

    echo = [not a.quiet]

    def pump():
        for line in iter(proc.stdout.readline, b""):
            sink.write(line)
            if echo[0]:
                try:
                    sys.stdout.buffer.write(line)
                    sys.stdout.flush()
                except (OSError, ValueError):  # the terminal went away (SIGHUP): keep recording, stop echoing
                    echo[0] = False

    started = time.time()
    man["started_utc"] = now()
    old = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    for s in old:
        signal.signal(s, lambda *_: stop("interrupted"))
    try:
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        except OSError as e:  # missing, not executable, no shebang, bad cwd ...
            status, rc = "launch-error", (127 if isinstance(e, FileNotFoundError) else 126)
            sink.write(f"labrun: could not start the command: {type(e).__name__}: {e}\n".encode())
        if proc is not None:
            mark_active(rid, child=proc.pid)  # so recover can stop an orphaned command if labrun itself dies
            reader = threading.Thread(target=pump, daemon=True)
            reader.start()
            timer = threading.Timer(a.timeout, stop, ("timeout",)) if a.timeout else None
            if timer:
                timer.daemon = True
                timer.start()
            _, wstatus, ru = os.wait4(proc.pid, 0)
            rc = os.waitstatus_to_exitcode(wstatus)
            proc.returncode = rc
            if timer:
                timer.cancel()
            reader.join(5)
            if reader.is_alive():  # background processes of the command still hold its output: stop them
                flags["lingering"] = True
                kill_group(signal.SIGTERM)
                reader.join(3)
                if reader.is_alive():
                    kill_group(signal.SIGKILL)
                    reader.join(2)
            finished.set()
            status = ("timeout" if flags["timeout"] else "interrupted" if flags["interrupted"]
                      else "failed" if rc != 0 else "ok")
    finally:
        for s, h in old.items():
            signal.signal(s, h)
        man["log"] = sink.close()

    man.update(status=status, exit_code=rc, ended_utc=now(), wall_s=round(time.time() - started, 3))
    if flags["lingering"]:
        man["note"] = "background processes still held the output after the command exited; they were stopped"
    if ru is not None:
        man.update(cpu_user_s=round(ru.ru_utime, 3), cpu_sys_s=round(ru.ru_stime, 3), max_rss_mb=round(ru.ru_maxrss / 1024, 1))
    finalize(a, man, rdir, cwd, before)
    return rc if isinstance(rc, int) else 1


def finalize(a, man, rdir, cwd, before):
    """Collect, bound, scan, record, commit and push the result of a run. Shared by run and recover."""
    rid = man["run_id"]
    out_root = os.path.join(rdir, "outputs")
    os.makedirs(out_root, exist_ok=True)
    limit = int(CFG["max_file_mb"] * 1048576)
    skipped = []
    roots = [os.path.realpath(cwd), os.path.realpath(repo_root())]
    for c in getattr(a, "collect", None) or []:
        src = os.path.join(cwd, c)
        real = os.path.realpath(src)
        if not any(real == r or real.startswith(r + os.sep) for r in roots):
            skipped.append(dict(path=c, reason="outside the working directory and the repository; not collected"))
            continue
        if not os.path.lexists(src):
            skipped.append(dict(path=c, reason="missing after run"))
            continue
        dst = out_root if os.path.isfile(src) else os.path.join(out_root, os.path.basename(os.path.normpath(c)))
        skipped += copy_tree(src, dst, c)[1]
    # over-limit, ignored, special and symlinked files leave the record (moved to data/, never deleted);
    # the record as a whole is capped too, largest files first
    entries = []
    for root, dirs, fs in os.walk(out_root):
        entries += [os.path.join(root, f) for f in fs]
        entries += [os.path.join(root, d) for d in dirs if os.path.islink(os.path.join(root, d))]
    total = 0
    for p in sorted(entries, key=lambda x: os.lstat(x).st_size):
        st = os.lstat(p)
        relp = os.path.relpath(p, out_root)
        if os.path.islink(p) or not os.path.isfile(p):
            skipped.append(dict(path=os.path.relpath(p, rdir), reason="symlink or special file, not recorded"))
            os.unlink(p)
            continue
        if st.st_size > limit or ignored(relp) or total + st.st_size > CFG.get("max_run_mb", 50) * 1048576:
            h = sha256_file(p)
            skipped.append(dict(path=os.path.relpath(p, rdir), bytes=st.st_size, sha256=h,
                                reason="over size limit, run cap, or ignored type", kept_locally=move_out(p, rid, rdir)))
        else:
            total += st.st_size
    # what the command changed in tracked files
    after = tracked_status() if before is not None else set()
    changed = sorted(after - (before or set()))
    if changed:
        files = [x[3:] for x in changed]
        diff = git("diff", "--", *files, check=False).stdout
        man["tracked_changes"] = dict(files=files, diff_bytes=len(diff.encode()))
        if 0 < len(diff.encode()) <= limit:
            with open(os.path.join(rdir, "tracked.diff"), "w", encoding="utf-8") as f:
                f.write(diff)
    allow = secretscan._load_allow()
    findings = []
    candidates = [os.path.join(rdir, x) for x in ("log.txt", "tracked.diff")]
    for root, _, fs in os.walk(out_root):
        candidates += [os.path.join(root, f) for f in fs]
    for f in candidates:
        if os.path.isfile(f) and not os.path.islink(f):
            for hit in secretscan.scan_file(f, allow, do_redact=True, label=os.path.relpath(f, rdir)):
                hit["path"] = f
                findings.append(hit)
    withheld = []
    for f in findings:
        if f["binary"] and os.path.exists(f["path"]):  # cannot redact in place: move it out of the record
            withheld.append(dict(path=secretscan.safe(os.path.relpath(f["path"], rdir)), reason=f"withheld: {f['kind']}",
                                 kept_locally=secretscan.safe(move_out(f["path"], rid, rdir))))
    man["redactions"] = [dict(file=f["file"], line=f["line"], kind=f["kind"]) for f in findings]
    man["withheld_files"] = withheld
    man["outputs"] = file_list(rdir)
    man["not_committed"] = skipped
    if os.path.exists(os.path.join(rdir, "log.txt")):
        man["log"] = dict(man.get("log") or {}, bytes=os.path.getsize(os.path.join(rdir, "log.txt")),
                          sha256=sha256_file(os.path.join(rdir, "log.txt")))
    summ = os.path.join(out_root, "summary.json")
    if os.path.exists(summ) and os.path.getsize(summ) < 200_000:
        try:
            man["summary"] = json.load(open(summ, encoding="utf-8"))
        except ValueError as e:
            man["summary"] = dict(error=f"summary.json is not valid JSON: {e}")
    man["verdict"] = evaluate(man["success_expr"], man) if man.get("success_expr") else None
    man, n_fields = sanitize(man)
    if n_fields:
        man["redactions"].append(dict(file="manifest.json", line=0, kind=f"{n_fields} field(s)"))
    write_json(os.path.join(rdir, "manifest.json"), man)
    unmark_active(rid)
    with git_lock():
        write_journal()
        if not getattr(a, "no_commit", False):
            commit([rdir, JOURNAL], f"run {rid}: {man['status']}" + (f", criterion {man['verdict']}" if man["verdict"] else "")
                   + (f" ({man['wall_s']:.1f}s)" if isinstance(man.get("wall_s"), (int, float)) else ""), [manifest_line(rdir)])
            if not getattr(a, "no_push", False):
                push(f"run {rid}")
    print(f"labrun: {rid} {man['status']} rc={man.get('exit_code')} wall={man.get('wall_s')}s "
          f"verdict={man['verdict']} -> {rel(rdir)}")


def cmd_recover(a):
    """Finalize runs started on this machine whose labrun process is gone (killed, OOM, machine restart)."""
    done = 0
    for f in sorted(os.listdir(_active_dir())):
        path = os.path.join(_active_dir(), f)
        entry = json.load(open(path, encoding="utf-8"))
        rid = f[:-5]
        if is_alive(entry):
            continue
        mpath = os.path.join(RUNS, rid, "manifest.json")
        man = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else None
        if not man or man.get("status") in FINAL_STATES:
            os.remove(path)
            continue
        child = entry.get("child")
        if child and entry.get("boot") == _boot_id() and _proc_start(child) == entry.get("child_start"):
            try:  # the command outlived its labrun: stop it, its result can no longer be recorded
                os.killpg(child, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
        man.update(status="lost", exit_code=None, ended_utc=now(),
                   note=f"labrun process {entry.get('pid')} was gone (killed, out of memory or machine restart); "
                        f"recovered {now()}; log.txt holds what was written before")
        finalize(argparse.Namespace(collect=[], no_commit=False, no_push=a.no_push), man,
                 os.path.join(RUNS, rid), repo_root(), None)
        done += 1
    print(f"labrun: recovered {done} lost run(s)")
    return 0


# ---------------------------------------------------------------- other commands
def cmd_checkpoint(a):
    limit = int(CFG["max_file_mb"] * 1048576)
    for spec in a.imports or []:
        src, _, dst = spec.partition(":")
        dst_dir = os.path.join(LAB, dst or os.path.basename(os.path.normpath(src)))
        copied, _ = copy_tree(src, dst_dir, "")
        big = []
        for c in copied:
            r = os.path.relpath(c, dst_dir)
            if os.path.getsize(c) > limit or ignored(r):
                big.append(dict(path=r, bytes=os.path.getsize(c), sha256=sha256_file(c)))
                os.remove(c)  # only the copy we just made; the original stays in the scratch directory
        if big:
            ptr = os.path.join(dst_dir, "LARGE_FILES.json")
            old = json.load(open(ptr, encoding="utf-8")) if os.path.exists(ptr) else []
            byname = {x["path"]: x for x in old}
            for s in big:
                byname[s["path"]] = dict(s, recorded_utc=now())
            write_json(ptr, sorted(byname.values(), key=lambda x: x["path"]))
        print(f"labrun: imported {len(copied) - len(big)} files from {src} into {rel(dst_dir)}; "
              f"{len(big)} large or ignored files recorded by sha256 only")
    with git_lock():
        lab_rel = rel(LAB)
        foreign = [x for x in git("diff", "--cached", "--name-only").stdout.splitlines() if not x.startswith(lab_rel + "/")]
        if foreign:
            raise LabError("checkpoint stopped: changes outside the lab are staged (" + ", ".join(foreign[:5]) +
                           "); commit or unstage them first, a lab checkpoint never carries them")
        status = git("status", "--porcelain", "-z", "--no-renames", "--untracked-files=all", "--", lab_rel).stdout
        changed = [os.path.join(repo_root(), e[3:]) for e in status.split("\0") if len(e) > 3 and e[:2].strip() != "D"]
        findings = []
        for p in changed:
            if os.path.isfile(p) and not os.path.islink(p):
                findings += secretscan.scan_file(p, secretscan._load_allow(), label=rel(p))
        if findings:
            for f in findings:
                print(f"labrun: {f['category']} {f['kind']} in {f['file']} line {f['line']}", file=sys.stderr)
            raise LabError("checkpoint stopped: remove these before saving (values are not shown)")
        big = [p for p in changed if os.path.isfile(p) and os.path.getsize(p) > limit]
        if big:
            raise LabError("checkpoint stopped: files over the size limit: " + ", ".join(rel(p) for p in big))
        write_journal()
        git("add", "--ignore-removal", "--", lab_rel)
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("labrun: nothing new to save")
            if has_pending() and not a.no_push:
                return 0 if push("pending commits", stored_branch=(read_pending() or {}).get("branch")) else 1
            return 0
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
    git("fetch", "-q", remote, f"+refs/heads/*:refs/remotes/{remote}/*", check=False, timeout=600)
    refs = [r for r in git("for-each-ref", "--format=%(refname)", f"refs/remotes/{remote}").stdout.split()
            if not r.endswith("/HEAD")]
    runs_rel = rel(RUNS)
    have = set(os.listdir(RUNS)) if os.path.isdir(RUNS) else set()
    added, sources, quarantined = [], {}, []
    allow = secretscan._load_allow()
    with git_lock():
        for ref in refs:
            ls = git("ls-tree", "-d", "--name-only", f"{ref}:{runs_rel}", check=False)
            if ls.returncode != 0:
                continue
            for rid in ls.stdout.split():
                if rid in have:
                    continue
                bad = []
                for line in git("ls-tree", "-r", ref, "--", f"{runs_rel}/{rid}").stdout.splitlines():
                    meta, path = line.split("\t", 1)
                    blob = subprocess.run(["git", "cat-file", "blob", meta.split()[2]], cwd=repo_root(),
                                          capture_output=True).stdout
                    bad += secretscan.scan_bytes(path, blob, allow)
                if bad:  # one bad record must not block everything else: leave it out and say so
                    quarantined.append(dict(run=secretscan.safe(rid), branch=ref.split("/", 3)[-1],
                                            kinds=sorted({b["kind"] for b in bad})))
                    have.add(rid)
                    continue
                git("checkout", ref, "--", f"{runs_rel}/{rid}")
                have.add(rid)
                added.append(rid)
                br = ref.split("/", 3)[-1]
                sources[br] = sources.get(br, 0) + 1
        if added:
            write_journal()
            commit([RUNS, JOURNAL], f"gather: {len(added)} run records from {len(sources)} branches",
                   [f"manifest-sha256 {rid}: {sha256_file(os.path.join(RUNS, rid, 'manifest.json'))}"
                    for rid in sorted(added) if os.path.exists(os.path.join(RUNS, rid, "manifest.json"))])
            if not a.no_push:
                push("gathered records")
    print(f"labrun: gathered {len(added)} run records from {len(sources)} branches {sources}"
          + (f"; left out {len(quarantined)} record(s) with findings: {quarantined}" if quarantined else ""))
    return 0


def cmd_sync(a):
    pend = read_pending()
    if not pend:
        print("labrun: nothing pending")
        return 0
    with git_lock():
        return 0 if push("pending commits", stored_branch=pend.get("branch")) else 1


def cmd_index(a):
    write_journal()
    print(f"labrun: {rel(JOURNAL)} rebuilt from {len(load_manifests())} runs")
    return 0


def cmd_status(a):
    try:
        target = push_target((read_pending() or {}).get("branch"))
    except LabError as e:
        target = f"refused ({e})"
    runs = load_manifests()
    active = []
    for f in sorted(os.listdir(_active_dir())):
        e = json.load(open(os.path.join(_active_dir(), f), encoding="utf-8"))
        active.append(dict(run_id=f[:-5], alive=is_alive(e)))
    print(json.dumps(dict(branch=current_branch(), push_target=target, pending_push=read_pending(), runs=len(runs),
                          active=active, last=[dict(run_id=m.get("run_id"), status=m.get("status"), verdict=m.get("verdict"))
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
    for name in ("gather", "recover"):
        x = sub.add_parser(name)
        x.add_argument("--no-push", action="store_true")
    for name in ("sync", "index", "status"):
        sub.add_parser(name)
    a = ap.parse_args(argv)
    try:
        return dict(run=cmd_run, checkpoint=cmd_checkpoint, gather=cmd_gather, recover=cmd_recover, sync=cmd_sync,
                    index=cmd_index, status=cmd_status)[a.command](a)
    except LabError as e:
        print(f"labrun: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
