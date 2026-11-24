#!/usr/bin/env python3
"""Scanner for credentials and personal data. Nothing leaves the lab without passing it.

Used three ways:
  * git hooks (pre-commit scans the staged blobs, commit-msg scans the message): a hit blocks the commit;
  * labrun.py, before every commit of a run: hits in text files are redacted in place,
    binary files with a hit are withheld;
  * bootstrap.sh / verify.py over the whole lab tree.

A matched value is never printed, logged or stored. Findings carry only the file, the line and the kind.
To allow one specific value, add a line "<kind> <first 16 hex of sha256(value)>" to secretscan.allow.

Exit codes: 0 clean, 1 at least one finding (or an error).
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOW_FILE = os.path.join(HERE, "secretscan.allow")
MAX_SCAN_BYTES = 50 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".venv-lab"}

# Credentials. Every pattern is anchored on a vendor prefix or a fixed structure, to keep false positives low.
SECRET = [
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai-key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("telegram-bot-token", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{33}\b")),
    ("kaggle-token", re.compile(r"\bKGAT_[A-Za-z0-9]{16,}")),
    ("kaggle-json-key", re.compile(r"""["']key["']\s*:\s*["'][0-9a-f]{32}["']""")),
    ("kaggle-env-key", re.compile(r"\bKAGGLE_(?:KEY|API_TOKEN)\s*[=:]\s*['\"]?[A-Za-z0-9_]{16,}")),
    ("auth-header", re.compile(r"(?i)\bauthorization\s*[:=]\s*['\"]?(?:bearer|basic|token)\s+[A-Za-z0-9._~+/=\-]{16,}")),
    ("url-credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@'\"]{1,64}:[^/\s@'\"]{6,}@[A-Za-z0-9.-]+")),
]
# key = "..." style assignments; reported only when the value looks random (see _looks_random).
GENERIC = re.compile(r"""(?i)\b[\w-]*(?:api[_-]?key|secret|token|passw(?:or)?d|credential)[\w-]*\s*[:=]\s*['"]([^'"\s]{16,})['"]""")

# Personal data. Israeli phone numbers (mobile and landline, local or +972) and e-mail addresses.
PII = [
    ("phone-il", re.compile(r"(?<![\w.+-])(?:\+972[-\s]?|0)(?:5\d(?:[-\s]?\d){7}|[23489](?:[-\s]?\d){7})(?![\w])(?!\.\d)")),
    ("email", re.compile(r"(?<![\w.+-])[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")),
]
EMAIL_ALLOW = re.compile(r"(?i)^(?:noreply@anthropic\.com|git@github\.com|git@gitlab\.com|[^@]+@(?:example\.(?:com|org|net)|users\.noreply\.github\.com))$")
PLACEHOLDER = re.compile(r"(?i)^(?:proxy|redacted|changeme|example|placeholder|dummy|test|xxx|\$\{|<|\*\*\*)")


def _digest(value):
    return hashlib.sha256(value.encode("utf-8", "surrogateescape")).hexdigest()[:16]


def _load_allow():
    allow = set()
    if os.path.exists(ALLOW_FILE):
        for line in open(ALLOW_FILE, encoding="utf-8"):
            parts = line.split("#", 1)[0].split()
            if len(parts) == 2:
                allow.add((parts[0], parts[1].lower()))
    return allow


def _looks_random(v):
    if PLACEHOLDER.match(v) or not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
        return False
    freq = {}
    for ch in v:
        freq[ch] = freq.get(ch, 0) + 1
    entropy = -sum(c / len(v) * math.log2(c / len(v)) for c in freq.values())
    return entropy >= 3.5


def find(text, allow=frozenset()):
    """Return a list of (start, end, line, kind, category) for every hit in text. Values are not returned."""
    hits = []
    def add(m, kind, cat, span=None):
        s, e = span or m.span()
        if (kind, _digest(text[s:e])) in allow:
            return
        hits.append((s, e, text.count("\n", 0, s) + 1, kind, cat))
    for kind, rx in SECRET:
        for m in rx.finditer(text):
            add(m, kind, "secret")
    for m in GENERIC.finditer(text):
        if _looks_random(m.group(1)):
            add(m, "generic-secret", "secret", m.span(1))
    for kind, rx in PII:
        for m in rx.finditer(text):
            if kind == "email" and EMAIL_ALLOW.match(m.group(0)):
                continue
            add(m, kind, "personal")
    # drop hits nested inside an earlier, wider hit
    hits.sort(key=lambda h: (h[0], -h[1]))
    out, last_end = [], -1
    for h in hits:
        if h[0] >= last_end:
            out.append(h)
            last_end = h[1]
    return out


def redact(text, hits):
    for s, e, _, kind, _ in sorted(hits, reverse=True):
        text = text[:s] + f"[REDACTED:{kind}]" + text[e:]
    return text


def _decode(data):
    binary = b"\0" in data[:8192]
    return data.decode("utf-8" if not binary else "latin-1", errors="surrogateescape"), binary


def scan_bytes(name, data, allow):
    text, binary = _decode(data)
    return [dict(file=name, line=(0 if binary else ln), kind=kind, category=cat, binary=binary)
            for _, _, ln, kind, cat in find(text, allow)]


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
                for f in sorted(files):
                    yield os.path.join(root, f)
        elif os.path.exists(p):
            yield p


def scan_paths(paths, allow, do_redact=False):
    findings, notes = [], []
    for f in iter_files(paths):
        if os.path.islink(f):
            continue
        size = os.path.getsize(f)
        if size > MAX_SCAN_BYTES:
            notes.append(f"not scanned (over {MAX_SCAN_BYTES >> 20} MB): {f}")
            continue
        data = open(f, "rb").read()
        text, binary = _decode(data)
        hits = find(text, allow)
        for _, _, ln, kind, cat in hits:
            findings.append(dict(file=f, line=0 if binary else ln, kind=kind, category=cat, binary=binary))
        if do_redact and hits and not binary:
            with open(f, "wb") as fh:
                fh.write(redact(text, hits).encode("utf-8", "surrogateescape"))
    return findings, notes


def staged_files():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def scan_staged(allow):
    findings = []
    for path in staged_files():
        size = int(subprocess.run(["git", "cat-file", "-s", f":{path}"], capture_output=True, text=True).stdout.strip() or 0)
        if size > MAX_SCAN_BYTES:
            findings.append(dict(file=path, line=0, kind="file-too-large-to-scan", category="secret", binary=True))
            continue
        data = subprocess.run(["git", "show", f":{path}"], capture_output=True, check=True).stdout
        findings += scan_bytes(path, data, allow)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--staged", action="store_true", help="scan the staged blobs (pre-commit hook)")
    ap.add_argument("--message-file", help="scan a commit message file (commit-msg hook)")
    ap.add_argument("--redact", action="store_true", help="redact hits in text files in place")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    allow = _load_allow()
    notes = []
    if a.staged:
        findings = scan_staged(allow)
    elif a.message_file:
        findings = scan_bytes("commit message", open(a.message_file, "rb").read(), allow)
    else:
        findings, notes = scan_paths(a.paths or ["."], allow, a.redact)
    if a.json:
        print(json.dumps(dict(findings=findings, notes=notes), ensure_ascii=False))
    else:
        for n in notes:
            print("note:", n, file=sys.stderr)
        for f in findings:
            print(f"{f['category']}: {f['kind']} in {f['file']}" + (f" line {f['line']}" if f["line"] else ""), file=sys.stderr)
        if findings and (a.staged or a.message_file):
            print("commit blocked by secretscan: remove the value, or allow one specific value in "
                  "lab/knowledge-frontier/infra/secretscan.allow (kind + sha256 prefix, never the value)", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
