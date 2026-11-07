#!/bin/bash
cd "$(dirname "$0")"
export G029_SCRATCH=/tmp/claude-0/-home-user/647f98b9-61ad-591f-af35-53bff0238e34/scratchpad
while pgrep -f run_scans.sh > /dev/null; do sleep 20; done
for c in "4 4 1048" "5 4 2254" "3 5 2173" "2 7 3703"; do
  timeout 1500 python3 deep_unknown.py $c 300 5 >> scans/deep.log 2>&1 &
done
wait
