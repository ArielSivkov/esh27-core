#!/bin/bash
# 4 workers; each scan capped at 25 min (checkpointed, restartable)
cd "$(dirname "$0")"
export G029_SCRATCH=/tmp/claude-0/-home-user/647f98b9-61ad-591f-af35-53bff0238e34/scratchpad
w() { for c in "$@"; do timeout 1500 python3 scan_orbit.py $c >> scans/worker.log 2>&1; done; }
w "4 4 1048 4 8 12" "4 4 1048 1.3 4 48" "6 4 9778 2 4 12" &
w "5 4 2254 3 6 12" "5 4 2254 1.3 4 48" "2 8 11495 2 4 12" &
w "3 5 2173 3 8 12" "3 5 2173 1.3 4 48" "3 6 11191 2 4 12" &
w "2 7 3703 3 8 24" "2 7 3703 1.3 4 96" "4 5 17705 2 4 12" &
wait
