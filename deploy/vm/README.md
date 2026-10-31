# CrownBot VM

Plan: "תוכנית: VM ושיחה קולית ל-CrownBot" (Claude Docs). One e2-small Ubuntu 24.04 VM in `me-west1`,
no open ports, reached only through a Cloudflare Tunnel. Nothing here has been run yet.

| File | Runs where | Does |
|---|---|---|
| `provision.sh` | Ariel's machine, `gcloud` logged in | service account, VM, firewall (IAP SSH only), daily snapshots |
| `bootstrap.sh` | on the VM, once | updates, Docker, `ufw`, clones this repo, secrets, `docker compose up` |
| `fetch-secrets.sh` | on the VM | Secret Manager → `deploy/vm/.env` (mode 600) |
| `docker-compose.yml` | on the VM | `control` (control center + `/mcp`) and `cloudflared` |

## Order

1. Billing on the GCP project is active, and a budget alert is set (Billing → Budgets).
2. `PROJECT=<id> ./deploy/vm/provision.sh`
3. Cloudflare (after DNS moved, `sites/CLOUDFLARE_MIGRATION.md` step 4): Zero Trust → Networks → Tunnels →
   create `crown`. Copy its token into Secret Manager as `tunnel-token`. Add one published application route:
   hostname `crown.esh27.com`, path `^/(control/(ask|status|telegram/webhook|voice/).*|mcp.*)$`,
   service `http://control:8080`. Every other path gets Cloudflare's 404 and never reaches the VM.
4. Secrets, from Ariel's terminal: `telegram-bot-token` (a NEW bot, not the leaked one), `telegram-admin-chat-id`,
   `telegram-webhook-secret`, `control-token`, `mcp-token`, `control-public-url` (`https://crown.esh27.com`).
   Twilio ones only in phase 4.
5. `gcloud compute ssh crown-vm --zone me-west1-a --tunnel-through-iap`, then
   `curl -fsSL https://raw.githubusercontent.com/ArielSivkov/esh27-core/claude/ecosystem-management-service-7yu9yk/deploy/vm/bootstrap.sh | bash`
   (or clone and run it).
6. Register the Telegram webhook as in the main README ("Control center").

## Acceptance (phase 2)

- `nmap -Pn <vm public ip>` from outside shows no open port.
- `curl https://crown.esh27.com/docs` → 404 from Cloudflare; `curl https://crown.esh27.com/control/status` → 401.
- SSH works only with `--tunnel-through-iap`.

After a secret changes: `sudo deploy/vm/fetch-secrets.sh && sudo docker compose up -d`.
