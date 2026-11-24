#!/usr/bin/env python3
"""Scanner for credentials and personal data. Nothing leaves the lab without passing it.

Used three ways:
  * git hooks (pre-commit scans the staged blobs and their paths, commit-msg scans the message): a hit blocks;
  * labrun.py, before every commit of a run: hits in text files are redacted in place, other files are withheld;
  * bootstrap.sh / verify.py over every file git tracks or would add in the lab tree.

A matched value is never printed, logged or stored; paths are printed only after redaction.
To allow one specific value, add a line "<kind> <first 16 hex of sha256(value)>" to secretscan.allow.
Known limits: a credential split across lines, base64-encoded or encrypted is not recognised.

Exit codes: 0 clean, 1 at least one finding (or a file that could not be scanned).
"""
import argparse
import gzip
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

# Credentials, anchored on a vendor prefix or a fixed structure to keep false positives low.
SECRET = [
    # the whole PEM/PGP block, body included; an unterminated block is redacted to the end of the text
    ("private-key", re.compile(r"-----BEGIN ((?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?)-----"
                               r"[\s\S]*?(?:-----END \1-----|\Z)")),
    ("github-token", re.compile(r"(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("huggingface-token", re.compile(r"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{30,}")),
    ("anthropic-key", re.compile(r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai-key", re.compile(r"(?<![A-Za-z0-9])sk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}")),
    ("google-api-key", re.compile(r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_\-]{35}")),
    ("google-oauth-secret", re.compile(r"(?<![A-Za-z0-9])GOCSPX-[A-Za-z0-9_\-]{20,}")),
    ("aws-access-key", re.compile(r"(?<![A-Za-z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Za-z0-9])")),
    ("aws-secret-key", re.compile(r"(?i)aws_secret_access_key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])")),
    ("slack-token", re.compile(r"(?<![A-Za-z0-9])xox[abposr]-[A-Za-z0-9-]{10,}")),
    ("slack-webhook", re.compile(r"(?i)https://hooks\.slack\.com/(?:services|workflows|triggers)/[A-Za-z0-9/_\-]{20,}")),
    ("telegram-bot-token", re.compile(r"(?<![0-9])\d{8,10}(?::|%3[Aa])AA[A-Za-z0-9_-]{33}(?![A-Za-z0-9_-])")),
    ("kaggle-token", re.compile(r"(?<![A-Za-z0-9])KGAT_[A-Za-z0-9]{16,}")),
    ("kaggle-json-key", re.compile(r"""["']username["']\s*:\s*["'][^"']*["']\s*,\s*["']key["']\s*:\s*["']([0-9a-f]{32})["']"""
                                   r"""|["']key["']\s*:\s*["']([0-9a-f]{32})["']\s*,\s*["']username["']""")),
    ("kaggle-env-key", re.compile(r"KAGGLE_(?:KEY|API_TOKEN)['\"\]]*\s*[=:]\s*['\"]?([A-Za-z0-9_]{16,})")),
    ("auth-header", re.compile(r"(?i)(?<![A-Za-z])authorization['\"]?\s*[:=]\s*['\"]?(?:bearer|basic|token)\s+([A-Za-z0-9._~+/=\-]{16,})")),
    ("url-credentials", re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@'\"<>]{1,64}:([^/\s@'\"<>]{3,})@[A-Za-z0-9.-]+")),
    ("url-query-secret", re.compile(r"(?i)[?&](?:access_token|refresh_token|id_token|token|api_key|apikey|key|secret|"
                                    r"client_secret|password|sig|signature|auth)=([^&\s#'\"]{8,})")),
    ("mysql-password", re.compile(r"(?i)\bmysql(?:dump|admin|import|check)?\b[^\n]*?\s-p([^\s'\"-][^\s'\"]{3,})")),
    ("cookie", re.compile(r"(?im)^[ \t]*(?:set-)?cookie[ \t]*:[ \t]*([^\r\n]{8,})|['\"](?:set-)?cookie['\"]\s*:\s*['\"]([^'\"]{8,})['\"]")),
    ("proxy-credentials", re.compile(r"(?i)\b(?:https?_|socks5?_|all_|ftp_)?proxy['\"]?\s*[:=]\s*['\"]?(?:[a-z][a-z0-9+.-]*://)?"
                                     r"[^\s:@/'\"]{1,64}:([^\s@/'\"]{3,})@")),
]
# key = "...", "key": "...", key: value, KEY=value. Reported only when the value looks random.
KEYWORD = r"(?:api[_-]?key|secret|token|passw(?:or)?d|passwd|credential|private[_-]?key|access[_-]?key)"
NOT_A_SECRET_NAME = re.compile(r"(?i)(?:_|-)(?:name|names|url|uri|path|file|files|dir|env|var|id|ids|hint|type|count|"
                               r"len|length|limit|ttl|field|header|prefix|suffix|label|key_name|scope|scopes)$")
Q = r"""(?:\\{0,3}["'])"""  # a quote, possibly escaped (JSON inside a JSON string, double-encoded logs)
GENERIC_QUOTED = re.compile(r"""(?i)(?<![\w.])""" + Q + r"""?([\w.-]*""" + KEYWORD + r"""[\w.-]*)""" + Q +
                            r"""?\s*[:=]\s*""" + Q + r"""([^"'\s\\]{8,})""" + Q)
GENERIC_BARE = re.compile(r"""(?im)^[ \t]*(?:export[ \t]+)?["']?([\w.-]*""" + KEYWORD +
                          r"""[\w.-]*)["']?[ \t]*[:=][ \t]*([^\s'"#,{}\[\]]{8,})[ \t]*(?:#.*)?$""")

# --password=..., --api-key VALUE ...: the command line of every run is recorded, so flag values are redacted even
# when they do not look random; counts and names (--max-tokens 512, --secret-name x) are not secrets
CLI_FLAG = re.compile(r"(?i)(?<![\w-])(--?[\w-]*(?:password|passwd|token|secret|api[_-]?key)[\w-]*)[= ]['\"]?([^\s'\"]{4,})")
CLI_NOT_SECRET = re.compile(r"(?i)(?:tokens|token[_-]?(?:count|limit|len|length|budget)|[_-](?:name|names|url|uri|path|"
                            r"file|files|dir|env|var|id|ids|hint|type|count|len|length|limit|ttl|field|header|prefix|"
                            r"suffix|label|scope|scopes))$")

# Personal data: Israeli phone numbers (any common spelling) and e-mail addresses.
PHONE = re.compile(r"""(?<![0-9.])(?:
        (?:(?:\+|00)[ \t]?)?972[ \t.-]?(?:\(0\)[ \t.-]?)?(?:[57]\d|[23489])     # international
      | \(?0(?:[57]\d|[23489]) )                                              # national
      \)?[ \t.-]{0,3}\d{3}[ \t.-]{0,3}\d{4}(?![0-9A-Za-z])""", re.X)
TLDS = ("com|org|net|edu|gov|mil|int|il|io|ai|co|me|app|dev|info|biz|uk|de|fr|ru|us|ca|au|nl|es|it|ch|se|no|fi|dk|pl|"
        "cz|at|be|jp|cn|in|br|mx|tv|xyz|online|site|tech|email|cloud|live|pro|ac|eu|ua|tr|gr|pt|ie|nz|za|kr|sg|hk")
EMAIL = re.compile(r"(?<![\w.+%])[A-Za-z0-9][A-Za-z0-9._%+-]*(?:@|%40)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:" + TLDS +
                   r")(?![A-Za-z0-9-])", re.I)
EMAIL_ALLOW = re.compile(r"(?i)^(?:git|noreply|no-reply|do-not-reply|donotreply)(?:@|%40)|"
                         r"(?:@|%40)(?:[\w-]+\.)*(?:example\.(?:com|org|net)|users\.noreply\.github\.com|gserviceaccount\.com)$")
PLACEHOLDER = re.compile(r"(?i)^(?:proxy|redacted|changeme|example|placeholder|dummy|test|xxx|your|<|\$\{|\$\(|\$[a-z_]|\*\*\*|%\()")


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
    if PLACEHOLDER.match(v) or "://" in v or v.startswith(("/", "./", "~")) or re.fullmatch(r"[A-Z0-9_]+", v):
        return False
    if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
        return False
    freq = {}
    for ch in v:
        freq[ch] = freq.get(ch, 0) + 1
    entropy = -sum(c / len(v) * math.log2(c / len(v)) for c in freq.values())
    return entropy >= 3.0


def _phone_ok(m):
    t = m.group(0)
    international = re.match(r"\(?(?:\+|00|972)", t) is not None
    # a bare 9-digit landline (02/03/04/08/09 + 7 digits) is too ambiguous; it counts only with a separator
    if not international and re.match(r"\(?0[23489]", t) and not re.match(r"\(?0[23489]\)?[ \t.-]", t):
        return False
    return True


def find(text, allow=frozenset()):
    """Return a list of (start, end, line, kind, category) for every hit in text. Values are not returned."""
    hits = []

    def add(kind, cat, s, e):
        if (kind, _digest(text[s:e])) not in allow:
            hits.append((s, e, text.count("\n", 0, s) + 1, kind, cat))

    for kind, rx in SECRET:
        for m in rx.finditer(text):
            g = [i for i in range(1, (rx.groups or 0) + 1) if m.group(i) is not None and kind not in ("private-key",)]
            if g and (m.group(g[-1])[0] in "<{$%" or PLACEHOLDER.match(m.group(g[-1]))):
                continue  # a placeholder such as <password>, {TOKEN} or $SECRET, not a value
            s, e = m.span(g[-1]) if g else m.span()
            add(kind, "secret", s, e)
    for rx in (GENERIC_QUOTED, GENERIC_BARE):
        for m in rx.finditer(text):
            name, value = m.group(1), m.group(2)
            if not NOT_A_SECRET_NAME.search(name) and _looks_random(value):
                add("generic-secret", "secret", *m.span(2))
    for m in CLI_FLAG.finditer(text):
        flag, value = m.group(1), m.group(2)
        plain_word = re.fullmatch(r"[A-Za-z]{1,11}", value) is not None  # prose such as "-token flag values"
        placeholder = (value.isdigit() or not re.search(r"[A-Za-z0-9]", value) or re.fullmatch(r"[A-Z][A-Z0-9_]*", value)
                       or value[0] in "{$<%" or PLACEHOLDER.match(value) or plain_word)
        if not CLI_NOT_SECRET.search(flag) and not placeholder:
            add("cli-secret-flag", "secret", *m.span(2))
    for m in PHONE.finditer(text):
        if _phone_ok(m):
            add("phone-il", "personal", *m.span())
    for m in EMAIL.finditer(text):
        if not EMAIL_ALLOW.search(m.group(0)):
            add("email", "personal", *m.span())
    hits.sort(key=lambda h: (h[0], -h[1]))  # keep the widest of overlapping hits
    out, last_end = [], -1
    for h in hits:
        if h[0] >= last_end:
            out.append(h)
            last_end = h[1]
        elif h[1] > last_end:  # partial overlap: extend the previous span
            s, _, ln, kind, cat = out[-1]
            out[-1] = (s, h[1], ln, kind, cat)
            last_end = h[1]
    return out


def redact(text, hits):
    for s, e, _, kind, _ in sorted(hits, reverse=True):
        text = text[:s] + f"[REDACTED:{kind}]" + text[e:]
    return text


def safe(text):
    """Text with every credential/personal value replaced; used for anything printed or stored."""
    return redact(text, find(text))


def decode(data):
    """Return (text, kind) where kind is text | utf16 | gzip | binary. gzip is scanned decompressed."""
    if data[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(data)[:MAX_SCAN_BYTES]
            return decode(raw)[0], "gzip"
        except (OSError, EOFError):
            pass
    if data[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(data) > 64 and data[1:64:2].count(0) > 28):
        try:
            return data.decode("utf-16"), "utf16"
        except UnicodeDecodeError:
            pass
    if b"\0" in data[:8192]:
        return data.decode("latin-1"), "binary"
    return data.decode("utf-8", errors="surrogateescape"), "text"


def scan_bytes(name, data, allow):
    text, kind = decode(data)
    out = [dict(file=safe(name), line=(ln if kind == "text" else 0), kind=k, category=cat, binary=kind != "text")
           for _, _, ln, k, cat in find(text, allow)]
    for _, _, _, k, cat in find(name, allow):
        out.append(dict(file=safe(name), line=0, kind=f"{k} (in the file name)", category=cat, binary=True))
    return out


def scan_file(path, allow, do_redact=False, label=None):
    """Scan one file. Returns findings; with do_redact, plain-text hits are redacted in place."""
    label = label or path
    if os.path.getsize(path) > MAX_SCAN_BYTES:
        return [dict(file=safe(label), line=0, kind="too large to scan", category="unscanned", binary=True)]
    data = open(path, "rb").read()
    text, kind = decode(data)
    hits = find(text, allow)
    out = [dict(file=safe(label), line=(ln if kind == "text" else 0), kind=k, category=cat, binary=kind != "text")
           for _, _, ln, k, cat in hits]
    for _, _, _, k, cat in find(label, allow):
        out.append(dict(file=safe(label), line=0, kind=f"{k} (in the file name)", category=cat, binary=True))
    if do_redact and hits and kind == "text":
        with open(path, "wb") as fh:
            fh.write(redact(text, hits).encode("utf-8", "surrogateescape"))
        for f in out:
            if "(in the file name)" not in f["kind"]:
                f["binary"] = False
    return out


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d != ".git")
                for f in sorted(files):
                    yield os.path.join(root, f)
        elif os.path.lexists(p):
            yield p


def scan_paths(paths, allow, do_redact=False):
    findings, notes = [], []
    for f in iter_files(paths):
        if os.path.islink(f) or not os.path.isfile(f):
            continue
        findings += scan_file(f, allow, do_redact)
    return findings, notes


def git_files(root):
    """Files under root that git tracks or would add (untracked, not ignored)."""
    p = subprocess.run(["git", "ls-files", "-z", "-co", "--exclude-standard", "--", "."], cwd=root,
                       capture_output=True, check=True)
    return [os.path.join(root, x) for x in p.stdout.decode("utf-8", "surrogateescape").split("\0") if x]


def staged_files():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z"],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def scan_staged(allow):
    findings = []
    for path in staged_files():
        size = int(subprocess.run(["git", "cat-file", "-s", f":{path}"], capture_output=True, text=True).stdout.strip() or 0)
        if size > MAX_SCAN_BYTES:
            findings.append(dict(file=safe(path), line=0, kind="too large to scan", category="unscanned", binary=True))
            continue
        data = subprocess.run(["git", "show", f":{path}"], capture_output=True, check=True).stdout
        findings += scan_bytes(path, data, allow)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--staged", action="store_true", help="scan the staged blobs (pre-commit hook)")
    ap.add_argument("--message-file", help="scan a commit message file (commit-msg hook)")
    ap.add_argument("--git-tree", help="scan every file git tracks or would add under this directory")
    ap.add_argument("--redact", action="store_true", help="redact hits in text files in place")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    allow = _load_allow()
    if a.staged:
        findings = scan_staged(allow)
    elif a.message_file:
        findings = scan_bytes("commit message", open(a.message_file, "rb").read(), allow)
    elif a.git_tree:
        findings = []
        for f in git_files(a.git_tree):
            if os.path.isfile(f) and not os.path.islink(f):
                findings += scan_file(f, allow, label=os.path.relpath(f, a.git_tree))
    else:
        findings, _ = scan_paths(a.paths or ["."], allow, a.redact)
    if a.json:
        print(json.dumps(dict(findings=findings), ensure_ascii=False))
    else:
        for f in findings:
            print(f"{f['category']}: {f['kind']} in {f['file']}" + (f" line {f['line']}" if f["line"] else ""), file=sys.stderr)
        if findings and (a.staged or a.message_file):
            print("commit blocked by secretscan: remove the value, or allow one specific value in "
                  "lab/knowledge-frontier/infra/secretscan.allow (kind + sha256 prefix, never the value)", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
