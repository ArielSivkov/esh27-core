#!/usr/bin/env bash
# ESH27 Lab — starter stack installer (Ubuntu 22.04/24.04)
# Idempotent: safe to re-run; each step checks before installing.
#
# Usage:
#   bash lab/scripts/setup.sh                 # core: apt deps, elan/Lean 4, Python venv
#   WITH_PYSR=1 bash lab/scripts/setup.sh     # + PySR (pulls Julia on first use, heavy)
#   WITH_KISSAT=1 bash lab/scripts/setup.sh   # + build Kissat and DRAT-trim from source
#   WITH_MATHLIB=1 bash lab/scripts/setup.sh  # + fetch mathlib cache in lab/lean (if a Lake project exists)
#
# Env overrides: LAB_DIR, VENV_DIR, TOOLS_DIR

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="${LAB_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
VENV_DIR="${VENV_DIR:-$LAB_DIR/.venv}"
TOOLS_DIR="${TOOLS_DIR:-$HOME/.local/esh27-tools}"
BIN_DIR="$HOME/.local/bin"

WITH_PYSR="${WITH_PYSR:-0}"
WITH_KISSAT="${WITH_KISSAT:-0}"
WITH_MATHLIB="${WITH_MATHLIB:-0}"

step() { printf '\n\033[1;34m==> [%s] %s\033[0m\n' "$1" "$2"; }
ok()   { printf '    \033[1;32m✓\033[0m %s\n' "$1"; }
skip() { printf '    \033[0;33m-\033[0m %s (already present, skipping)\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

mkdir -p "$TOOLS_DIR" "$BIN_DIR"

# ---------------------------------------------------------------- 1. apt
step 1 "System packages (git, curl, build tools, python3-venv)"
APT_PKGS=(git curl ca-certificates build-essential python3 python3-venv python3-pip pkg-config)
MISSING=()
for p in "${APT_PKGS[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || MISSING+=("$p")
done
if ((${#MISSING[@]})); then
  SUDO=""; [[ $EUID -ne 0 ]] && SUDO="sudo"
  echo "    installing: ${MISSING[*]}"
  $SUDO apt-get update -y
  $SUDO apt-get install -y "${MISSING[@]}"
  ok "apt packages installed"
else
  skip "apt packages"
fi

# ---------------------------------------------------------------- 2. elan / Lean 4
step 2 "elan + Lean 4 toolchain"
export PATH="$HOME/.elan/bin:$BIN_DIR:$PATH"
if have elan; then
  skip "elan ($(elan --version 2>/dev/null | head -1))"
else
  curl -sSfL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --default-toolchain stable
  ok "elan installed"
fi
elan toolchain list 2>/dev/null | grep -q stable || elan toolchain install stable
ok "lean: $(lean --version 2>/dev/null || echo 'available after new shell')"
ok "lake: $(lake --version 2>/dev/null || echo 'available after new shell')"

# ---------------------------------------------------------------- 3. Python venv
step 3 "Python virtualenv at $VENV_DIR"
if [[ -x "$VENV_DIR/bin/python" ]]; then
  skip "venv"
else
  python3 -m venv "$VENV_DIR"
  ok "venv created"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --quiet --upgrade pip wheel

step 4 "Python starter packages"
PY_PKGS=(sympy numpy scipy networkx python-sat z3-solver mpmath pandas openpyxl matplotlib jupyter requests anthropic claude-agent-sdk)
# pip is idempotent: already-satisfied packages are skipped.
python -m pip install --quiet "${PY_PKGS[@]}"
python - <<'PY'
import importlib
mods = ["sympy","numpy","scipy","networkx","pysat","z3","mpmath","pandas","openpyxl","matplotlib","anthropic"]
for m in mods:
    try:
        mod = importlib.import_module(m)
        print(f"    ✓ {m} {getattr(mod,'__version__','')}")
    except Exception as e:
        print(f"    ✗ {m}: {e}")
PY

# ---------------------------------------------------------------- 5. optional PySR
step 5 "PySR (optional, WITH_PYSR=1)"
if [[ "$WITH_PYSR" == "1" ]]; then
  if python -c "import pysr" 2>/dev/null; then
    skip "pysr"
  else
    python -m pip install --quiet pysr
    ok "pysr installed (Julia backend is downloaded on first 'import pysr' — heavy)"
  fi
else
  echo "    skipped (set WITH_PYSR=1 to enable)"
fi

# ---------------------------------------------------------------- 6. optional Kissat + DRAT-trim
step 6 "Kissat + DRAT-trim (optional, WITH_KISSAT=1)"
if [[ "$WITH_KISSAT" == "1" ]]; then
  if have kissat; then
    skip "kissat ($(kissat --version))"
  else
    [[ -d "$TOOLS_DIR/kissat" ]] || git clone --depth 1 https://github.com/arminbiere/kissat.git "$TOOLS_DIR/kissat"
    (cd "$TOOLS_DIR/kissat" && ./configure && make -j"$(nproc)")
    ln -sf "$TOOLS_DIR/kissat/build/kissat" "$BIN_DIR/kissat"
    ok "kissat -> $BIN_DIR/kissat"
  fi
  if have drat-trim; then
    skip "drat-trim"
  else
    [[ -d "$TOOLS_DIR/drat-trim" ]] || git clone --depth 1 https://github.com/marijnheule/drat-trim.git "$TOOLS_DIR/drat-trim"
    (cd "$TOOLS_DIR/drat-trim" && make)
    ln -sf "$TOOLS_DIR/drat-trim/drat-trim" "$BIN_DIR/drat-trim"
    ok "drat-trim -> $BIN_DIR/drat-trim"
  fi
else
  echo "    skipped (set WITH_KISSAT=1 to enable)"
fi

# ---------------------------------------------------------------- 7. optional mathlib cache
step 7 "mathlib cache (optional, WITH_MATHLIB=1)"
if [[ "$WITH_MATHLIB" == "1" ]]; then
  if [[ -f "$LAB_DIR/lean/lakefile.lean" || -f "$LAB_DIR/lean/lakefile.toml" ]]; then
    (cd "$LAB_DIR/lean" && lake exe cache get && lake build)
    ok "mathlib cache fetched and project built"
  else
    echo "    no Lake project in $LAB_DIR/lean yet — skipping"
  fi
else
  echo "    skipped (set WITH_MATHLIB=1 to enable)"
fi

# ---------------------------------------------------------------- done
step ✓ "Done"
cat <<EOF
    Next steps:
      source "$VENV_DIR/bin/activate"
      export PATH="\$HOME/.elan/bin:$BIN_DIR:\$PATH"
      export ANTHROPIC_API_KEY=...   # for Claude API / Agent SDK
    Web tools (no install): LeanSearch, Loogle, OEIS, arXiv API, LMFDB.
EOF
