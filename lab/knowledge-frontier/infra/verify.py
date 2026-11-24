#!/usr/bin/env python3
"""Verify a (re)built lab against infra/expected.json. Offline by default; --data adds the rebuilt-data checks.

Prints one line per check (PASS / FAIL / SKIP with the reason) and writes a JSON report with --json-out.
Exit code 1 if any check failed. A SKIP is never counted as a pass.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import secretscan  # noqa: E402

EXP = json.load(open(os.path.join(HERE, "expected.json"), encoding="utf-8"))
RESULTS = []


def record(check, ok, detail, skip=False):
    RESULTS.append(dict(check=check, result="SKIP" if skip else ("PASS" if ok else "FAIL"), detail=detail))


def load(rel):
    return json.load(open(os.path.join(LAB, rel), encoding="utf-8"))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


STUB = r'''
import sys, types, os, runpy, hashlib
class Stop(Exception): pass
def stop(*a, **k): raise Stop()
t = types.ModuleType("torch"); t.cuda = types.SimpleNamespace(is_available=lambda: False)
t.no_grad = lambda: (lambda f: f); t.float32 = "float32"; t.set_num_threads = lambda n: None
tr = types.ModuleType("transformers")
tr.AutoTokenizer = types.SimpleNamespace(from_pretrained=stop); tr.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=stop)
pf = types.ModuleType("peft"); pf.LoraConfig = pf.get_peft_model = pf.PeftModel = None
sys.modules.update(torch=t, transformers=tr, peft=pf)
script = sys.argv[1]
sys.argv = [script]          # the generator reads sys.argv[1] as ROUNDS; give it none
try:
    runpy.run_path(script, run_name="__main__")
except Stop:
    pass
'''


def check_frozen_sets():
    """The frozen test sets must be exactly what the committed generator code produces from its seed."""
    for e in EXP["frozen_sets"]:
        name = f"frozen-set regenerates: {e['file']}"
        committed = os.path.join(LAB, e["file"])
        if sha(committed) != e["sha256"]:
            record(name, False, "committed file changed (sha256 differs from expected.json)")
            continue
        with tempfile.TemporaryDirectory() as d:
            script = os.path.join(d, os.path.basename(e["script"]))
            with open(script, "wb") as f:
                f.write(open(os.path.join(LAB, e["script"]), "rb").read())
            stub = os.path.join(d, "stub_run.py")
            with open(stub, "w") as f:
                f.write(STUB)
            p = subprocess.run([sys.executable, "-I", stub, script], cwd=d, capture_output=True, text=True,
                               env={"SEED": e["seed"], "PATH": os.environ.get("PATH", "")}, timeout=120)
            out = os.path.join(d, os.path.basename(e["file"]))
            if not os.path.exists(out):
                record(name, False, f"generator wrote nothing (rc={p.returncode}): {(p.stderr.strip().splitlines() or [''])[-1][:300]}")
                continue
            got = sha(out)
            record(name, got == e["sha256"], f"sha256 {got[:16]} (expected {e['sha256'][:16]}), seed {e['seed']}, "
                   f"Python {sys.version.split()[0]}")


def close(a, b, tol):
    return abs(float(a) - float(b)) <= tol


def check_artifacts():
    A = EXP["artifacts"]
    # topology, arXiv up to 2021, symmetric IPF null model
    e = A["ipf_out"]
    rows = load(e["file"])
    r = [x["r"] for x in rows]
    med, low = statistics.median(r), sum(v < 0.15 for v in r)
    ok = len(rows) == e["rows"] and close(med, e["median"], 0.0005) and low == e["below_0_15"]
    record("artifact matches log: ipf_out.json", ok, f"rows {len(rows)}, median {med:.3f}, below 0.15: {low} ({e['source']})")
    by = {tuple(x["t"]): x for x in rows}
    bad = [t for t, obs, exp in e["triangles"] if tuple(t) not in by or by[tuple(t)]["obs"] != obs
           or not close(by[tuple(t)]["ipf"], exp, 0.05)]
    record("artifact matches log: three named holes", not bad, f"{len(e['triangles']) - len(bad)}/{len(e['triangles'])} match")
    e = A["timetest"]
    got = load(e["file"])
    ok = len(got) == len(e["rows"]) and all(g[0] == w[0] and g[1] == w[1] and g[2] == w[2] and close(g[3], w[3], 0.001)
                                            for g, w in zip(got, e["rows"]))
    record("artifact matches log: time test", ok, f"{[g[:3] for g in got]} ({e['source']})")
    e = A["nullmodel"]
    n = len(load(e["file"])["real_hollow"])
    record("artifact matches log: null model", n == e["real_hollow"], f"real hollow {n} ({e['source']})")
    e = A["verify_out"]
    row = [x for x in load(e["file"])["rows"] if x["tri"] == e["triangle"]]
    record("artifact matches log: raw recount", bool(row) and row[0]["ABC"] == e["ABC"],
           f"ABC {row[0]['ABC'] if row else 'missing'} ({e['source']})")
    e = A["hollow_triangles"]
    h = load(e["file"])
    ok = len(h) == e["rows"] and [h[0][1], h[0][3]] == e["first"] and [h[1][1], h[1][3]] == e["second"]
    record("artifact matches log: first hollow triangles", ok, f"{len(h)} rows ({e['source']})")
    e = A["oac_counts"]
    n = load(e["file"])["N"]
    record("artifact matches log: OpenAlex counts", n == e["N"], f"N {n} ({e['source']})")
    e = A["seal_local"]
    hist = load(e["file"])
    means, ctrl = [x["test"]["mean"] for x in hist], [x["control"] for x in hist]
    ok = all(close(a, b, 0.0005) for a, b in zip(means, e["means"])) and all(close(a, b, 0.0005) for a, b in zip(ctrl, e["control"]))
    record("artifact matches log: SEAL local run", ok and len(means) == len(e["means"]), f"means {means}, control {ctrl}")


def check_recompute():
    for name, e in EXP["recompute"].items():
        cwd = os.path.join(LAB, e["cwd"])
        with tempfile.TemporaryDirectory() as d:
            # run in a scratch copy so the check never writes into the repo
            for f in glob.glob(os.path.join(cwd, "*.json")) + [os.path.join(LAB, e["script"])]:
                with open(os.path.join(d, os.path.basename(f)), "wb") as out:
                    out.write(open(f, "rb").read())
            p = subprocess.run([sys.executable, "-I", os.path.basename(e["script"]), *e["args"]], cwd=d,
                               capture_output=True, text=True, timeout=600)
        first = (p.stdout.splitlines() or [""])[0].strip()
        record(f"recompute: {name}", p.returncode == 0 and first == e["stdout_first_line"],
               first if p.returncode == 0 else f"rc={p.returncode} {(p.stderr.strip().splitlines() or [''])[-1][:300]}")


def check_code_compiles():
    """Every Python source compiles: .py files (hidden ones too), notebook code cells, python-shebang scripts."""
    skip = {".git", ".venv", "data", "__pycache__"}
    sources = []
    for root, dirs, files in os.walk(LAB):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith(".py"):
                sources.append((path, open(path, "rb").read().decode("utf-8", "replace")))
            elif f.endswith(".ipynb"):
                try:
                    nb = json.load(open(path, encoding="utf-8"))
                    for i, c in enumerate(nb.get("cells", [])):
                        if c.get("cell_type") == "code":
                            src = "".join(c.get("source", [])) if isinstance(c.get("source"), list) else c.get("source", "")
                            code = "\n".join("" if ln.lstrip().startswith(("!", "%")) else ln for ln in src.splitlines())
                            sources.append((f"{path}#cell{i}", code))
                except ValueError as e:
                    sources.append((path, f"raise SyntaxError({str(e)!r})"))
            elif "." not in f and os.path.isfile(path) and not os.path.islink(path):
                head = open(path, "rb").read(80)
                if head.startswith(b"#!") and b"python" in head.split(b"\n")[0]:
                    sources.append((path, open(path, "rb").read().decode("utf-8", "replace")))
    bad = []
    for name, code in sources:
        try:
            compile(code, name, "exec")
        except SyntaxError as e:
            bad.append(f"{os.path.relpath(name, LAB)}: line {e.lineno}: {e.msg}"[:150])
    record("all Python sources compile (files, notebook cells, scripts)", not bad,
           f"{len(sources) - len(bad)}/{len(sources)} on Python {sys.version.split()[0]}" + (f"; {bad[:3]}" if bad else ""))


def check_no_secrets():
    allow = secretscan._load_allow()
    try:
        files = secretscan.git_files(LAB)
    except Exception:  # not a git checkout: scan the directory
        files = list(secretscan.iter_files([LAB]))
    findings = []
    for f in files:
        if os.path.isfile(f) and not os.path.islink(f):
            findings += secretscan.scan_file(f, allow, label=os.path.relpath(f, LAB))
    detail = f"{len(files)} files, {len(findings)} findings" + (
        ": " + ", ".join(f"{f['kind']} in {f['file']}" for f in findings[:5]) if findings else "")
    record("no credentials or personal data in the lab tree", not findings, detail)


def check_pins():
    bad, n = [], 0
    for e in EXP.get("pinned", {}).get("files", []):
        path = os.path.join(LAB, e["file"])
        n += 1
        if not os.path.exists(path):
            bad.append(f"{e['file']} missing")
            continue
        data = open(path, "rb").read()
        if "prefix_bytes" in e:
            data = data[: e["prefix_bytes"]]
            if len(data) < e["prefix_bytes"]:
                bad.append(f"{e['file']} shorter than its pinned part")
                continue
        if hashlib.sha256(data).hexdigest() != e["sha256"]:
            bad.append(f"{e['file']} changed")
    record("pinned result files unchanged (sha256)", not bad, f"{n - len(bad)}/{n}" + (f"; {bad[:5]}" if bad else ""))


def check_runs():
    runs = sorted(glob.glob(os.path.join(LAB, "runs", "*", "manifest.json")))
    final = {"ok", "failed", "timeout", "interrupted", "launch-error", "lost"}
    bad = []
    for m in runs:
        man = json.load(open(m, encoding="utf-8"))
        d = os.path.dirname(m)
        for o in man.get("outputs", []):
            p = os.path.join(d, o["path"])
            if not os.path.exists(p) or sha(p) != o["sha256"]:
                bad.append(f"{man.get('run_id')}: {o['path']}")
        if man.get("status") in final:
            lg = (man.get("log") or {}).get("sha256")
            p = os.path.join(d, "log.txt")
            if lg and (not os.path.exists(p) or sha(p) != lg):
                bad.append(f"{man.get('run_id')}: log.txt")
            if man.get("schema", 1) >= 2 and not lg and man.get("status") != "lost":
                bad.append(f"{man.get('run_id')}: final status without a log hash")
    record("run records intact (sha256 of every output and log)", not bad,
           f"{len(runs)} runs checked" + (f"; broken: {bad[:5]}" if bad else ""))
    check_run_seals(runs)


def git_out(*args):
    p = subprocess.run(["git", *args], cwd=LAB, capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def check_run_seals(runs):
    """A run record must be exactly what labrun committed: its manifest matches a manifest-sha256 seal written by
    labrun's own commit for that run (or a gather/seal commit naming it) at or after its last change, its history
    is one registration plus at most one result (or one gather that added it), no other commit touched it, and
    every run ever registered on this branch still has its record.
    What this detects: accidental and ordinary edits, deletions, and commits that only imitate labrun's text.
    What it cannot detect: a rewritten history (force push) or a record that labrun itself was fed false data for.
    Real tamper evidence needs signed commits or an external append-only log."""
    name = "run records sealed in git history (no later edits, nothing deleted)"
    if git_out("rev-parse", "--is-inside-work-tree") is None:
        record(name, False, "not a git checkout", skip=True)
        return
    if (git_out("rev-parse", "--is-shallow-repository") or "").strip() == "true":
        record(name, False, "shallow clone: history not available (bootstrap.sh makes a full clone)", skip=True)
        return
    log = git_out("log", "--format=%H%x1f%B%x1e") or ""
    order, seals, registered, subject_of = {}, {}, set(), {}
    for i, chunk in enumerate(x for x in log.split("\x1e") if x.strip()):
        h, _, body = chunk.strip("\n").partition("\x1f")
        order[h] = i
        subj = body.split("\n", 1)[0]
        subject_of[h] = subj
        m = re.match(r"run (\S+): (\S+)", subj)
        if m and m.group(2) == "registered":
            registered.add(m.group(1))
        named_ok = subj.startswith(("gather: ", "seal: "))
        for line in body.splitlines():
            g = re.match(r"manifest-sha256 (\S+): ([0-9a-f]{64})$", line.strip())
            if g and named_ok:
                seals.setdefault(g.group(1), []).append((g.group(2), i))
            elif m and re.match(r"manifest-sha256: ([0-9a-f]{64})$", line.strip()):
                seals.setdefault(m.group(1), []).append((line.strip().split()[-1], i))
    bad, legacy = [], []
    present = set()
    for mpath in runs:
        rid = os.path.basename(os.path.dirname(mpath))
        present.add(rid)
        touching = (git_out("log", "--format=%H", "--", os.path.relpath(os.path.dirname(mpath), LAB)) or "").split()
        if not touching:
            bad.append(f"{rid}: record not committed")
            continue
        foreign = [h for h in touching if not (subject_of.get(h, "").startswith(f"run {rid}: ")
                                                or subject_of.get(h, "").startswith("gather: "))]
        if foreign:
            bad.append(f"{rid}: changed by a commit that is not labrun's: {foreign[0][:9]} {subject_of.get(foreign[0], '')[:50]!r}")
            continue
        # the only legal shapes: one registration and at most one final commit, or one gather commit that ADDED
        # the whole folder; a second result commit or a gather that modifies an existing record is a rewrite
        regs = [h for h in touching if subject_of[h] == f"run {rid}: registered"]
        finals = [h for h in touching if subject_of[h].startswith(f"run {rid}: ") and h not in regs]
        gathers = [h for h in touching if subject_of[h].startswith("gather: ")]
        shape_ok = (len(regs) == 1 and len(finals) <= 1 and not gathers) or (not regs and not finals and len(gathers) == 1)
        if gathers and shape_ok:
            st = git_out("show", "--name-status", "--format=", gathers[0], "--", os.path.relpath(os.path.dirname(mpath), LAB)) or ""
            shape_ok = all(line.startswith("A\t") for line in st.splitlines() if line.strip())
        if not shape_ok:
            bad.append(f"{rid}: its history is not one registration plus one result (or one gather that added it)")
            continue
        last = (git_out("log", "-1", "--format=%H", "--", os.path.relpath(mpath, LAB)) or "").strip()
        cur = sha(mpath)
        if not any(hx == cur and idx <= order.get(last, -1) for hx, idx in seals.get(rid, [])):
            (legacy if not seals.get(rid) else bad).append(rid if seals.get(rid) is None else f"{rid}: manifest differs from its seal")
    missing = sorted(registered - present)
    bad += [f"{r}: registered in history but its record is gone" for r in missing]
    detail = f"{len(runs) - len(bad) - len(legacy)}/{len(runs)} sealed"
    if legacy:
        detail += f"; {len(legacy)} without any seal: {legacy[:3]}"
    if bad:
        detail += f"; failed: {bad[:5]}"
    record(name, not bad and not legacy, detail)


def check_data():
    D = EXP["data"]
    e = D["arxiv_2021"]
    p = os.path.join(LAB, e["file"])
    if not os.path.exists(p):
        record("data: arXiv to 2021", False, "not built (run infra/build_data.py arxiv2021)", skip=True)
    else:
        d = json.load(open(p))
        meta = p + ".meta.json"
        lines = json.load(open(meta)).get("lines") if os.path.exists(meta) else len(d)
        ok = lines == e["papers"]
        record("data: arXiv to 2021 paper count", ok, f"{lines} records read, {len(d)} unique ids (expected {e['papers']})")
        if ok:
            with tempfile.TemporaryDirectory() as t:
                os.symlink(p, os.path.join(t, "arxiv_all_cats.json"))
                with open(os.path.join(t, "ipf.py"), "wb") as f:
                    f.write(open(os.path.join(LAB, "topo", "ipf.py"), "rb").read())
                r = subprocess.run([sys.executable, "-I", "ipf.py"], cwd=t, capture_output=True, text=True, timeout=7200)
                new = json.load(open(os.path.join(t, "ipf_out.json"))) if r.returncode == 0 else []
            old = load("topo/ipf_out.json")
            key = lambda x: tuple(x["t"])
            om, nm = {key(x): x for x in old}, {key(x): x for x in new}
            same = om.keys() == nm.keys() and all(om[k]["obs"] == nm[k]["obs"] and abs(om[k]["ipf"] - nm[k]["ipf"]) < 1e-6 for k in om)
            record("data: ipf.py on rebuilt data reproduces ipf_out.json", same, f"{len(nm)} triangles rebuilt vs {len(om)} committed")
    e = D["arxiv_2026"]
    p = os.path.join(LAB, e["file"])
    if not os.path.exists(p):
        record("data: arXiv to 2026", False, "not built (run infra/build_data.py arxiv2026)", skip=True)
    else:
        d = json.load(open(p))
        last = max(d, key=lambda k: (k.split(".")[0], k.split(".")[-1].zfill(5)) if "." in k and "/" not in k else ("", ""))
        record("data: arXiv to 2026", len(d) == e["papers"] and last == e["last_id"], f"{len(d)} papers, last id {last}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", action="store_true", help="also check rebuilt raw data (slow)")
    ap.add_argument("--json-out")
    a = ap.parse_args()
    for fn in (check_code_compiles, check_frozen_sets, check_artifacts, check_pins, check_recompute, check_no_secrets,
               check_runs):
        try:
            fn()
        except Exception as e:  # a crashing check is a failed check, never a silent one
            record(fn.__name__, False, f"check crashed: {type(e).__name__}: {e}")
    if a.data:
        check_data()
    for r in RESULTS:
        print(f"{r['result']:4}  {r['check']}  — {r['detail']}")
    n = {k: sum(r["result"] == k for r in RESULTS) for k in ("PASS", "FAIL", "SKIP")}
    print(f"verify: {n['PASS']} pass, {n['FAIL']} fail, {n['SKIP']} skipped")
    report = dict(headline=f"{n['PASS']} pass, {n['FAIL']} fail, {n['SKIP']} skipped (Python {sys.version.split()[0]})",
                  counts=n, results=RESULTS, python=sys.version.split()[0])
    for path in filter(None, [a.json_out, os.environ.get("LAB_RUN_OUT") and os.path.join(os.environ["LAB_RUN_OUT"], "summary.json")]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    if n["FAIL"]:
        return 1
    return 3 if n["SKIP"] else 0  # a check that could not run is not a success (exit 3 = incomplete)


if __name__ == "__main__":
    sys.exit(main())
