#!/usr/bin/env python3
"""Probe which compute/data hosts this machine can reach (list in infra/lab.json "hosts").

A host that answers with any HTTP status is reachable. A proxy refusal (CONNECT 403/407), DNS failure or
timeout is reported by host name and kind; nothing is retried around it and no data is invented for it.
"""
import argparse
import concurrent.futures as cf
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "lab.json"), encoding="utf-8"))


def probe(host, url, timeout):
    t = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "esh27-lab-probe/1"})
    res = dict(host=host)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res.update(state="reachable", http=r.status)
    except urllib.error.HTTPError as e:
        res.update(state="reachable", http=e.code)
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "Tunnel connection failed" in reason or "403" in reason or "407" in reason:
            res.update(state="blocked-by-proxy", detail=reason[:120])
        elif isinstance(e.reason, socket.gaierror):
            res.update(state="dns-failure", detail=reason[:120])
        elif isinstance(e.reason, (socket.timeout, TimeoutError)):
            res.update(state="timeout")
        else:
            res.update(state="error", detail=reason[:120])
    except (socket.timeout, TimeoutError):
        res.update(state="timeout")
    except Exception as e:  # report, never hide
        res.update(state="error", detail=f"{type(e).__name__}: {e}"[:120])
    res["ms"] = round((time.time() - t) * 1000)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--timeout", type=float, default=12)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(lambda kv: probe(kv[0], kv[1], a.timeout), CFG["hosts"].items()))
    out = dict(checked_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), results=res,
               reachable=[r["host"] for r in res if r["state"] == "reachable"],
               blocked=[r["host"] for r in res if r["state"] != "reachable"])
    out["headline"] = f"{len(out['reachable'])} reachable, {len(out['blocked'])} blocked: {', '.join(out['blocked']) or '-'}"
    if os.environ.get("LAB_RUN_OUT"):
        with open(os.path.join(os.environ["LAB_RUN_OUT"], "summary.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        for r in res:
            print(f"{r['state']:17} {r['host']:26} {r.get('http', '')} {r['ms']} ms")
        print(f"hosts: {len(out['reachable'])} reachable, {len(out['blocked'])} blocked: {', '.join(out['blocked']) or '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
