#!/usr/bin/env bash
# Writes deploy/vm/.env (root only) from Secret Manager. Secret names are the env names in lower case
# with dashes, e.g. TELEGRAM_BOT_TOKEN -> telegram-bot-token. Missing secrets are skipped, and every
# feature that needs one stays off (the control center fails closed).
# To add one, from Ariel's own terminal (never in chat or git):
#   printf %s 'value' | gcloud secrets create telegram-bot-token --data-file=-
set -euo pipefail

OUT=$(dirname "$0")/.env
NAMES="TELEGRAM_BOT_TOKEN TELEGRAM_ADMIN_CHAT_ID TELEGRAM_WEBHOOK_SECRET CONTROL_TOKEN MCP_TOKEN
CONTROL_PUBLIC_URL CONTROL_PHONE TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN TWILIO_FROM TUNNEL_TOKEN"

umask 077
: > "$OUT"
for name in $NAMES; do
  secret=$(echo "$name" | tr 'A-Z_' 'a-z-')
  if value=$(gcloud secrets versions access latest --secret "$secret" 2>/dev/null); then
    printf '%s=%s\n' "$name" "$value" >> "$OUT"
    echo "ok      $name"
  else
    echo "missing $name"
  fi
done
