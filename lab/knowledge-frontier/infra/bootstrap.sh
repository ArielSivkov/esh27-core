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

step "1 clone $REPO_URL -> $TARGET (full history: needed to check the run seals)"
if [ -d "$TARGET/.git" ]; then
  git -C "$TARGET" fetch -q origin '+refs/heads/*:refs/remotes/origin/*'
  if [ "$(git -C "$TARGET" rev-parse --is-shallow-repository)" = true ]; then git -C "$TARGET" fetch -q --unshallow origin || true; fi
else
  GIT_LFS_SKIP_SMUDGE=1 git clone -q --no-single-branch "$REPO_URL" "$TARGET"
fi
cd "$TARGET"

step "2 choose the branch whose lab tools changed last"
# by the newest commit that touched $LAB_REL/infra, not by the newest tip: an old copy of the tools on a
# branch with an unrelated new commit must never win
best=""; best_t=0; best_tip=0; lab_t_of_best=0; others=""
for ref in $(git for-each-ref --format='%(refname)' refs/remotes/origin); do
  case "$ref" in */HEAD) continue;; esac
  git cat-file -e "$ref:$LAB_REL/README.md" 2>/dev/null || continue
  lab_t=$(git log -1 --format=%ct "$ref" -- "$LAB_REL" ":(exclude)$LAB_REL/runs" ":(exclude)$LAB_REL/JOURNAL.md")
  if git cat-file -e "$ref:$LAB_REL/infra/labrun.py" 2>/dev/null; then
    t=$(git log -1 --format=%ct "$ref" -- "$LAB_REL/infra"); tip=$(git log -1 --format=%ct "$ref")
    if [ "$t" -gt "$best_t" ] || { [ "$t" -eq "$best_t" ] && [ "$tip" -gt "$best_tip" ]; }; then
      [ -n "$best" ] && others="$others ${best#refs/remotes/origin/}@$lab_t_of_best"
      best="$ref"; best_t="$t"; best_tip="$tip"; lab_t_of_best="${lab_t:-0}"
    else
      others="$others ${ref#refs/remotes/origin/}@${lab_t:-0}"
    fi
  else
    others="$others ${ref#refs/remotes/origin/}@${lab_t:-0}"
  fi
done
if [ -n "${LAB_SOURCE_BRANCH:-}" ]; then
  best="refs/remotes/origin/$LAB_SOURCE_BRANCH"
  git rev-parse -q --verify "$best" >/dev/null || die "LAB_SOURCE_BRANCH=$LAB_SOURCE_BRANCH does not exist on $REPO_URL"
  lab_t_of_best=$(git log -1 --format=%ct "$best" -- "$LAB_REL" ":(exclude)$LAB_REL/runs" ":(exclude)$LAB_REL/JOURNAL.md")
fi
[ -n "$best" ] || die "no branch on $REPO_URL contains $LAB_REL/infra/labrun.py (lab branches without the tools:${others:- none})"
branch="${best#refs/remotes/origin/}"
for x in $others; do
  if [ "${x##*@}" -gt "${lab_t_of_best:-0}" ]; then
    echo "warning: ${x%@*} has newer lab changes (besides run records) than $branch; review and merge them"
  fi
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
"$PY" -m venv --clear "$LAB_REL/.venv"
VPY="$PWD/$LAB_REL/.venv/bin/python"
"$VPY" -m pip install -q --disable-pip-version-check -r "$LAB_REL/infra/requirements-verify.txt"
"$VPY" -c 'import numpy, yaml; print("numpy", numpy.__version__, "pyyaml", yaml.__version__)'

step "4 git hooks: block credentials and personal data"
git config core.hooksPath "$LAB_REL/infra/hooks"
git config user.name >/dev/null || git config user.name "lab-bootstrap"
git config user.email >/dev/null || git config user.email "lab-bootstrap@localhost"

step "5 gather run records from every branch (local commit, no push); finalize runs that died here"
LAB_NO_PUSH=1 "$VPY" "$LAB_REL/infra/labrun.py" gather --no-push || echo "warning: gather failed; continuing with this branch's records"
LAB_NO_PUSH=1 "$VPY" "$LAB_REL/infra/labrun.py" recover --no-push || echo "warning: recover failed"

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
    [ "$rc" -eq 0 ] && rc=3   # data was asked for and could not be built: not a success
  fi
fi

step "done"
echo "bootstrap: branch $branch, verify exit $rc, total $(( $(date +%s) - T0 )) s"
exit $rc
