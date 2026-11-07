#!/usr/bin/env bash
# Build the pinned SAT tool-chain used by G050 into ./tools (git-ignored).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p tools && cd tools
CADICAL_REV=c60730422e758ef1cebe7aeddf2dda31c996bf04   # CaDiCaL 3.0.1
DRATTRIM_REV=2e3b2dc0ecf938addbd779d42877b6ed69d9a985  # drat-trim + lrat-check
[ -d cadical ] || git clone -q https://github.com/arminbiere/cadical.git
[ -d drat-trim ] || git clone -q https://github.com/marijnheule/drat-trim.git
(cd cadical && git checkout -q "$CADICAL_REV" 2>/dev/null || true; ./configure >/dev/null && make -j4 -s >/dev/null)
(cd drat-trim && git checkout -q "$DRATTRIM_REV" 2>/dev/null || true; make -s >/dev/null 2>&1)
ls -l cadical/build/cadical drat-trim/drat-trim drat-trim/lrat-check
