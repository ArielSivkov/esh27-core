#!/usr/bin/env bash
# Copies the static subdomain sites from the Hostinger backup into sites/<name>/ for Cloudflare Pages.
# Usage: scripts/import-hostinger-backup.sh <backup_dir>
#   <backup_dir> has one folder per site, named <name>.esh27.com or <name> (e.g. shuru.esh27.com/).
#   The static front of esh27.com itself (esh27.com/static/) goes to sites/portal/.
# Only static files are copied. PHP, .htaccess, Hostinger's default page and anything that
# looks like a secret are left out, and the script lists what it skipped.
set -euo pipefail

backup=${1:?usage: $0 <backup_dir>}
root=$(cd "$(dirname "$0")/.." && pwd)
names="portal shuru farms neomi jaale danda game academy status books news security"

for name in $names; do
  src=""
  if [ "$name" = portal ]; then
    cands=("$backup/esh27.com/static" "$backup/portal")
  else
    cands=("$backup/$name.esh27.com" "$backup/$name" "$backup/public_html/$name")
  fi
  for cand in "${cands[@]}"; do
    [ -d "$cand" ] && { src=$cand; break; }
  done
  if [ -z "$src" ]; then
    echo "MISSING  $name (no folder in $backup)"
    continue
  fi
  dest="$root/sites/$name"
  mkdir -p "$dest"
  # Hostinger's subdomain folders sometimes keep the site under public_html/.
  [ -d "$src/public_html" ] && src="$src/public_html"
  skipped=$(cd "$src" && find . -type f \( -name '*.php' -o -name '.htaccess' -o -name '.user.ini' -o -name '*.env' \
    -o -name '.env*' -o -name '*.sql' -o -name '*.bak' -o -name '*.log' -o -name 'wp-config*' \) | sort)
  (cd "$src" && find . -type f ! -name '*.php' ! -name '.htaccess' ! -name '.user.ini' ! -name '*.env' \
    ! -name '.env*' ! -name '*.sql' ! -name '*.bak' ! -name '*.log' ! -name 'wp-config*' -print0 \
    | xargs -0 -I{} cp --parents "{}" "$dest/")
  # Pages is case-sensitive; Hostinger was not (2702/ had Index.html). Rename via a temp name, which also
  # works on Windows, where Index.html and index.html are the same file.
  if [ -f "$dest/Index.html" ]; then
    mv "$dest/Index.html" "$dest/index.html.tmp.$$" && mv -f "$dest/index.html.tmp.$$" "$dest/index.html"
  fi
  count=$(find "$dest" -type f | wc -l)
  size=$(du -sh "$dest" | cut -f1)
  echo "OK       $name: $count files, $size  (from $src)"
  [ -n "$skipped" ] && echo "$skipped" | sed "s|^\.|         skipped $name|"
  [ -f "$dest/index.html" ] || echo "WARNING  $name has no index.html, so it will not be deployed"
done
echo
echo "Next: review sites/*/ (git status), commit, and push to main to deploy."
