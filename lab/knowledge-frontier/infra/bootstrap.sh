#!/usr/bin/env bash
# Rebuild the Knowledge Frontier lab on an empty machine, then prove it is intact.
#
#   bash bootstrap.sh [TARGET_DIR]          (default ./esh27-core)
#   curl -fsSL https://raw.githubusercontent.com/ArielSivkov/esh27-core/<branch>/lab/knowledge-frontier/infra/bootstrap.sh | bash
#
# Needs only git and python3 (>= 3.9). Steps, each timed:
#   1 clone (all branch tips, shallow)  2 pick the newest branch that holds the lab tools
#   3 python venv with exact versions    4 install the git hooks that block keys and personal data
#   5 gather run records from every branch  6 probe hosts (blocked ones are named, never worked around)
#   7 verify against infra/expected.json  8 with LAB_DATA=1: rebuild raw data from mirrors and verify it
#
# Environment: LAB_REPO_URL (default the GitHub repo), LAB_SOURCE_BRANCH (force a branch), LAB_PYTHON,
#              LAB_DATA=1 (also rebuild data). Proxy/CA variables of the machine are used as they are.
set -euo pipefail
REPO_URL="${LAB_REPO_URL:-https://github.com/ArielSivkov/esh27-core}"
TARGET="${1:-$PWD/esh27-core}"
PY="${LAB_PYTHON:-python3}"
LAB_REL="lab/knowledge-frontier"
T0=$(date +%s)
step() { printf '\n== %s (%ss)\n' "$1" "$(( $(date +%s) - T0 ))"; }
die() { echo "bootstrap: $*" >&2; exit 2; }

command -v git >/dev/null || die "git is missing (apt-get install -y git)"
command -v "$PY" >/dev/null || die "$PY is missing (apt-get install -y python3 python3-venv)"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || die "python >= 3.9 needed"

step "1 clone $REPO_URL -> $TARGET"
if [ -d "$TARGET/.git" ]; then
  git -C "$TARGET" fetch -q --depth 1 origin '+refs/heads/*:refs/remotes/origin/*'
else
  GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 --no-single-branch "$REPO_URL" "$TARGET"
fi
cd "$TARGET"

step "2 choose the newest branch that holds $LAB_REL/infra/labrun.py"
best=""; best_t=0; newer_without_tools=""
for ref in $(git for-each-ref --format='%(refname)' refs/remotes/origin); do
  case "$ref" in */HEAD) continue;; esac
  t=$(git log -1 --format=%ct "$ref")
  if git cat-file -e "$ref:$LAB_REL/infra/labrun.py" 2>/dev/null; then
    if [ "$t" -gt "$best_t" ]; then best="$ref"; best_t="$t"; fi
  elif git cat-file -e "$ref:$LAB_REL/README.md" 2>/dev/null; then
    newer_without_tools="$newer_without_tools ${ref#refs/remotes/origin/}@$t"
  fi
done
if [ -n "${LAB_SOURCE_BRANCH:-}" ]; then best="refs/remotes/origin/$LAB_SOURCE_BRANCH"; fi
[ -n "$best" ] || die "no branch on $REPO_URL contains $LAB_REL/infra/labrun.py (lab branches without the tools:${newer_without_tools:- none})"
branch="${best#refs/remotes/origin/}"
for x in $newer_without_tools; do
  if [ "${x##*@}" -gt "$best_t" ]; then echo "warning: ${x%@*} has newer lab content but no tools; merge it into $branch"; fi
done
if git rev-parse -q --verify "refs/heads/$branch" >/dev/null && ! git merge-base --is-ancestor "refs/heads/$branch" "$best"; then
  # a re-run must never throw away local commits that were not pushed yet (labrun keeps them as pending)
  ahead=$(git rev-list --count "$best..refs/heads/$branch")
  echo "warning: local $branch has $ahead commit(s) not on the remote; keeping them (push later with: labrun.py sync)"
  git checkout -q "$branch"
else
  git checkout -q -B "$branch" "$best"
fi
echo "branch: $branch ($(git log -1 --format='%h %ci' HEAD))"

step "3 python environment ($("$PY" --version 2>&1)) with exact versions"
"$PY" -m venv "$LAB_REL/.venv"
VPY="$PWD/$LAB_REL/.venv/bin/python"
"$VPY" -m pip install -q --disable-pip-version-check -r "$LAB_REL/infra/requirements-verify.txt"
"$VPY" -c 'import numpy, yaml; print("numpy", numpy.__version__, "pyyaml", yaml.__version__)'

step "4 git hooks: block credentials and personal data"
git config core.hooksPath "$LAB_REL/infra/hooks"
git config user.name >/dev/null || git config user.name "lab-bootstrap"
git config user.email >/dev/null || git config user.email "lab-bootstrap@localhost"

step "5 gather run records from every branch (local commit, no push)"
LAB_NO_PUSH=1 "$VPY" "$LAB_REL/infra/labrun.py" gather --no-push

step "6 hosts"
"$VPY" "$LAB_REL/infra/hosts.py" | tee "$LAB_REL/infra/.last_hosts.txt"

step "7 verify"
set +e
"$VPY" "$LAB_REL/infra/verify.py" --json-out "$LAB_REL/infra/.last_verify.json"
rc=$?
set -e

if [ "${LAB_DATA:-0}" = "1" ]; then
  step "8 rebuild raw data from Hugging Face mirrors"
  if grep -q '^reachable *huggingface.co' "$LAB_REL/infra/.last_hosts.txt"; then
    "$VPY" -m pip install -q --disable-pip-version-check -r "$LAB_REL/infra/requirements-data.txt"
    for job in arxiv2021 arxiv2026 openalex; do "$VPY" "$LAB_REL/infra/build_data.py" "$job" || rc=1; done
    "$VPY" "$LAB_REL/infra/verify.py" --data --json-out "$LAB_REL/infra/.last_verify_data.json" || rc=1
  else
    echo "huggingface.co is not reachable from this machine: raw data not rebuilt (nothing invented in its place)"
  fi
fi

step "done"
echo "bootstrap: branch $branch, verify exit $rc, total $(( $(date +%s) - T0 )) s"
exit $rc
