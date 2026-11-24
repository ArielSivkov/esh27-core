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
import py_compile
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
    files = [f for f in glob.glob(os.path.join(LAB, "**", "*.py"), recursive=True) if "/.venv/" not in f]
    bad = []
    with tempfile.TemporaryDirectory() as d:
        for f in files:
            try:
                py_compile.compile(f, cfile=os.path.join(d, "x.pyc"), doraise=True)
            except py_compile.PyCompileError as e:
                bad.append(f"{os.path.relpath(f, LAB)}: {e.msg.splitlines()[-1][:120]}")
    record("all Python files compile", not bad, f"{len(files) - len(bad)}/{len(files)}" + (f"; {bad[:3]}" if bad else ""))


def check_no_secrets():
    findings, notes = secretscan.scan_paths([LAB], secretscan._load_allow())
    detail = f"{len(findings)} findings" + (": " + ", ".join(f"{f['kind']} in {os.path.relpath(f['file'], LAB)}" for f in findings[:5]) if findings else "")
    record("no credentials or personal data in the lab tree", not findings, detail + (f"; {notes}" if notes else ""))


def check_runs():
    runs = sorted(glob.glob(os.path.join(LAB, "runs", "*", "manifest.json")))
    bad = []
    for m in runs:
        man = json.load(open(m, encoding="utf-8"))
        d = os.path.dirname(m)
        for o in man.get("outputs", []):
            p = os.path.join(d, o["path"])
            if not os.path.exists(p) or sha(p) != o["sha256"]:
                bad.append(f"{man.get('run_id')}: {o['path']}")
        if man.get("status") not in ("registered",) and "log" in man:
            p = os.path.join(d, "log.txt")
            if not os.path.exists(p) or sha(p) != man["log"]["sha256"]:
                bad.append(f"{man.get('run_id')}: log.txt")
    record("run records intact (sha256 of every output and log)", not bad,
           f"{len(runs)} runs checked" + (f"; broken: {bad[:5]}" if bad else ""))


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
    for fn in (check_code_compiles, check_frozen_sets, check_artifacts, check_recompute, check_no_secrets, check_runs):
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
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(dict(results=RESULTS, counts=n, python=sys.version.split()[0]), f, ensure_ascii=False, indent=1)
    return 1 if n["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
