#!/usr/bin/env bash
# Copies the static subdomain sites from the Hostinger backup into sites/<name>/ for Cloudflare Pages.
# Usage: scripts/import-hostinger-backup.sh <backup_dir>
#   <backup_dir> has one folder per site, named <name>.esh27.com or <name> (e.g. shuru.esh27.com/).
# Only static files are copied. PHP, .htaccess, Hostinger's default page and anything that
# looks like a secret are left out, and the script lists what it skipped.
set -euo pipefail

backup=${1:?usage: $0 <backup_dir>}
root=$(cd "$(dirname "$0")/.." && pwd)
names="shuru farms neomi jaale danda game academy status books news security"

for name in $names; do
  src=""
  for cand in "$backup/$name.esh27.com" "$backup/$name" "$backup/public_html/$name"; do
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
  [ -f "$dest/Index.html" ] && [ ! -f "$dest/index.html" ] && mv "$dest/Index.html" "$dest/index.html"
  count=$(find "$dest" -type f | wc -l)
  size=$(du -sh "$dest" | cut -f1)
  echo "OK       $name: $count files, $size  (from $src)"
  [ -n "$skipped" ] && echo "$skipped" | sed "s|^\.|         skipped $name|"
  [ -f "$dest/index.html" ] || echo "WARNING  $name has no index.html, so it will not be deployed"
done
echo
echo "Next: review sites/*/ (git status), commit, and push to main to deploy."
