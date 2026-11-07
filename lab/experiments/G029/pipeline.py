#!/usr/bin/env python3
"""End-to-end: orbit CSP -> integer colouring of length (k-1)zp+1 -> repair wildcard
slots with lsearch -> verify with verify.py AND verify2 -> log to runs.jsonl.
Usage: pipeline.py r k p z R [record] [--save]"""
import sys, json, os, subprocess, time, hashlib
import numpy as np
from orbit_csp import solve, classes
from verify import first_mono_ap

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.environ.get('G029_SCRATCH', '/tmp/claude-0/-home-user/647f98b9-61ad-591f-af35-53bff0238e34/scratchpad')

def log(rec):
    rec["timestamp"] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    with open(os.path.join(HERE, 'runs.jsonl'), 'a') as fh:
        fh.write(json.dumps(rec) + '\n')

def build(r, k, p, z, R, f):
    m = z * p; cl = classes(p, z, R)
    cyc = np.where(cl >= 0, np.asarray(f)[np.maximum(cl, 0)], -1)
    N = (k - 1) * m + 1
    col = []
    for t in range(N):
        c = int(cyc[t % m])
        if c < 0:   # wildcard slot t = j*p : colour like a nearby non-wildcard  (repaired later)
            j = t // p; c = int(cyc[(j % m)]) if cyc[j % m] >= 0 else j % r
        col.append(c)
    return col

def run(r, k, p, z, R, record=None, save=False, tlim_ls=60):
    info, f = solve(r, k, p, z, R)
    info["method"] = "orbit-csp"
    if f is None:
        log(info); return info
    col = build(r, k, p, z, R, f)
    fn = os.path.join(SCR, f"cand_{r}_{k}_{p}_{z}_{R}.txt")
    open(fn, 'w').write(''.join(map(str, col)) + '\n')
    ok2 = subprocess.run([os.path.join(HERE, 'verify2'), fn, str(r), str(k)], capture_output=True).returncode == 0
    if not ok2:
        out = fn + '.fix'
        pr = subprocess.run([os.path.join(HERE, 'lsearch'), fn, str(r), str(k), str(len(col)), '1',
                             '100000000', '50', str(p), out, str(tlim_ls)], capture_output=True, text=True)
        info["repair"] = pr.stdout.strip()
        if pr.returncode == 0: fn = out; col = [int(ch) for ch in open(fn).read().strip()]
        else:
            info["status"] = "SAT-but-repair-failed"; log(info); return info
    ok2 = subprocess.run([os.path.join(HERE, 'verify2'), fn, str(r), str(k)], capture_output=True).returncode == 0
    ok1 = first_mono_ap(col, r, k) is None
    info.update(f=''.join(map(str, f)), verified_py=ok1, verified_c=ok2, n_good=len(col) if ok1 and ok2 else None)
    if record is not None: info["record"] = record; info["beats_record"] = bool(ok1 and ok2 and len(col) > record)
    if save and ok1 and ok2:
        sub = 'certificates' if info.get("beats_record") else 'certificates/reproduced'
        path = os.path.join(HERE, sub, f"W{r}_{k}_gt{len(col)}_orbit_p{p}_z{z}_R{R}.txt")
        open(path, 'w').write(''.join(map(str, col)) + '\n')
        info["cert"] = os.path.relpath(path, HERE); info["sha256"] = hashlib.sha256(open(path,'rb').read()).hexdigest()
    log(info); return info

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    r, k, p, z, R = map(int, a[:5]); rec = int(a[5]) if len(a) > 5 else None
    print(json.dumps(run(r, k, p, z, R, rec, '--save' in sys.argv)))
