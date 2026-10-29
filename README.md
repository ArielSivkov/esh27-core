# esh27-core
esh27 AI Ecosystem Microservices Backend

## MCP gateway (`/mcp`)

The cloud node of the ESH27 Federated MCP Mesh. Streamable HTTP at `/mcp`.

- Requires `Authorization: Bearer <MCP_TOKEN>`. Without `MCP_TOKEN` the endpoint refuses every call.
  Before merging to `main`, add the `MCP_TOKEN` secret in GitHub (Settings → Secrets → Actions).
- Tools: `esh27_health`, `esh27_generate`; plus `residual_land_value`, `sale_deals_near`,
  `land_tenders` when the developer-hub package is installed.
- Local: `MCP_ALLOW_ANON=1 uvicorn backend.api.main:app --port 8080`
