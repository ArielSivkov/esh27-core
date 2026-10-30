# backend/api/mcp_gateway.py
"""
MCP gateway for esh27-core: the cloud node of the ESH27 Federated MCP Mesh.

Serves MCP over streamable HTTP at /mcp, so Claude, Cursor or the local
gateway (127.0.0.1:4000) can call esh27 tools.

- Always exposes esh27 tools (health, generate via Vertex).
- If the developer-hub package (`hub`) is installed, also exposes its
  real-estate tools (sale deals, ILA tenders, residual land value).
- Every /mcp request must send `Authorization: Bearer <MCP_TOKEN>`. Without MCP_TOKEN
  the endpoint refuses all calls (set MCP_ALLOW_ANON=1 only for local dev).
"""

from __future__ import annotations

import hmac
import logging
import os
import time

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from starlette.responses import JSONResponse

from backend.models.vertex_llm import GenerateRequest, get_default_llm

logger = logging.getLogger("esh27-core.mcp")

server = _Server(
    name="esh27-sovereign-core",
    instructions="ESH27 cloud core: text generation and, when installed, Israeli real-estate tools.",
)

_STARTED = time.time()


@server.tool()
def esh27_health() -> dict:
    """Service status and which tool groups are loaded."""
    return {"status": "ok", "service": "esh27-core", "uptime_s": int(time.time() - _STARTED),
            "tool_groups": TOOL_GROUPS}


@server.tool()
async def esh27_generate(prompt: str, language: str = "he", length: int = 512) -> dict:
    """Generate text with the esh27 Vertex model."""
    resp = await get_default_llm().generate_async(
        GenerateRequest(prompt=prompt, language=language, length=length))
    return resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)


TOOL_GROUPS = ["esh27", "control"]


def _control():
    from backend.control.router import get_control
    return get_control()


@server.tool()
def ask_ariel(agent: str, question: str, options: list[str] | None = None,
              urgency: str = "normal", sensitive: bool = False) -> dict:
    """Ask Ariel a question through CrownBot (Telegram; phone call if 'blocking' and unanswered).

    urgency: info | normal | blocking. sensitive=True for payments, uploads to the live
    site or messages sent in Ariel's name: it needs a second confirmation in Telegram.
    Returns the request with its id; poll get_ariel_answer. If it expires, do not act.
    """
    from backend.control.service import Paused
    try:
        return _control().ask(agent, question, options, urgency, sensitive).public()
    except Paused as exc:
        return {"status": "paused", "detail": str(exc)}


@server.tool()
def get_ariel_answer(request_id: str) -> dict:
    """Status and answer of a request made with ask_ariel (open | answered | expired)."""
    req = _control().store.get(request_id)
    return req.public() if req else {"status": "not_found"}


@server.tool()
def control_status() -> dict:
    """Whether Ariel paused all agents (/stop), and how many questions wait for him."""
    return _control().status()

try:
    from hub.mcp_server import land_tenders, residual_land_value, sale_deals_near
except ImportError:
    logger.info("developer-hub not installed; real-estate tools disabled")
else:
    for fn in (residual_land_value, sale_deals_near, land_tenders):
        server.add_tool(fn)
    TOOL_GROUPS.append("developer-hub")


def http_app():
    """Starlette app serving MCP at /mcp. Its lifespan must run (see main.py)."""
    return server.streamable_http_app(stateless_http=True, json_response=True, host="0.0.0.0")


class BearerAuth:
    """ASGI middleware: require MCP_TOKEN on /mcp."""

    def __init__(self, app, path_prefix: str = "/mcp"):
        self.app = app
        self.prefix = path_prefix
        self.token = os.getenv("MCP_TOKEN", "")
        # Fail closed: without a token /mcp is refused, unless explicitly opened for local dev.
        self.open = os.getenv("MCP_ALLOW_ANON") == "1"

    async def __call__(self, scope, receive, send):
        if not self.open and scope["type"] == "http" and scope["path"].startswith(self.prefix):
            sent = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
            if not self.token or not hmac.compare_digest(sent, f"Bearer {self.token}"):
                await JSONResponse({"detail": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)
