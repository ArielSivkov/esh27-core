# esh27-core
esh27 AI Ecosystem Microservices Backend

## MCP gateway (`/mcp`)

The cloud node of the ESH27 Federated MCP Mesh. Streamable HTTP at `/mcp`.

- Requires `Authorization: Bearer <MCP_TOKEN>`. Without `MCP_TOKEN` the endpoint refuses every call.
  Before merging to `main`, add the `MCP_TOKEN` secret in GitHub (Settings → Secrets → Actions).
- Tools: `esh27_health`, `esh27_generate`; plus `residual_land_value`, `sale_deals_near`,
  `land_tenders` when the developer-hub package is installed.
- Local: `MCP_ALLOW_ANON=1 uvicorn backend.api.main:app --port 8080`

## Control center: CrownBot (`/control`)

Agents ask Ariel; he answers in Telegram; if a `blocking` question is not answered, his phone rings.

- **Agents:** MCP tools `ask_ariel`, `get_ariel_answer`, `control_status`, or HTTP
  `POST /control/ask` / `GET /control/ask/{id}` with `Authorization: Bearer <CONTROL_TOKEN>` (falls back to `MCP_TOKEN`).
  An expired question means **do not act**.
- **Escalation:** reminder after 5 min; for `blocking`, phone calls at 10 and 25 min, expiry at 60.
  No reminders or calls on Shabbat (Fri 15:00 – Sat 20:30) and no calls at night (`CONTROL_NIGHT`, default `23-7`).
- **Sensitive** (`sensitive=true`: payments, uploads to the live site, messages in Ariel's name):
  a second click in Telegram; never approved by phone or free text.
- **Telegram commands** (only from `TELEGRAM_ADMIN_CHAT_ID`): `/pending`, `/status`, `/stop` (pauses every agent), `/resume`.
- **The ladder runs** on `POST /control/tick` (Cloud Scheduler every minute) or in-process with `CONTROL_TICK_SECONDS=60`.

| Env | What |
|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID` | CrownBot token from BotFather; Ariel's numeric user id |
| `TELEGRAM_WEBHOOK_SECRET` | random string, also passed to `setWebhook` as `secret_token` |
| `CONTROL_TOKEN` | bearer for agents and the tick |
| `CONTROL_PUBLIC_URL` | public base URL (Twilio callbacks and signature check) |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `CONTROL_PHONE` | phone escalation; off until all are set |
| `CONTROL_DB` | SQLite path. On Cloud Run run with `--max-instances=1` until this moves to Firestore |

Register the webhook once (from a terminal, never paste the token into chat or git):

```
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d url="$CONTROL_PUBLIC_URL/control/telegram/webhook" \
  -d secret_token="$TELEGRAM_WEBHOOK_SECRET" -d allowed_updates='["message","callback_query"]'
```

Tests: `python -m unittest discover -s tests -t .`
