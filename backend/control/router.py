"""
HTTP endpoints of the control center.

Agents   POST /control/ask, GET /control/ask/{id}, GET /control/status   Bearer CONTROL_TOKEN (or MCP_TOKEN)
Cron     POST /control/tick                                              Bearer CONTROL_TOKEN (or MCP_TOKEN)
Telegram POST /control/telegram/webhook        header X-Telegram-Bot-Api-Secret-Token = TELEGRAM_WEBHOOK_SECRET
Twilio   POST /control/voice/twiml/{id}, /control/voice/gather/{id}      X-Twilio-Signature
All of them fail closed when their secret is not set.
"""

from __future__ import annotations

import hmac
import os
from functools import lru_cache

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.control import voice
from backend.control.service import Control, Paused

router = APIRouter(prefix="/control", tags=["control"])


@lru_cache(maxsize=1)
def get_control() -> Control:
    return Control()


def _same(a: str, b: str) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(a, b)


def agent_auth(authorization: str = Header(default="")) -> None:
    token = os.getenv("CONTROL_TOKEN") or os.getenv("MCP_TOKEN", "")
    if not _same(authorization, f"Bearer {token}" if token else ""):
        raise HTTPException(status_code=401, detail="unauthorized")


class AskIn(BaseModel):
    agent: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=1500)
    options: list[str] = Field(default_factory=lambda: ["כן", "לא"], max_length=4)
    urgency: str = Field(default="normal", pattern="^(info|normal|blocking)$")
    sensitive: bool = False


@router.post("/ask", dependencies=[Depends(agent_auth)])
def ask(body: AskIn, control: Control = Depends(get_control)) -> dict:
    try:
        return control.ask(body.agent, body.question, body.options, body.urgency, body.sensitive).public()
    except Paused as exc:
        raise HTTPException(status_code=423, detail=str(exc))


@router.get("/ask/{rid}", dependencies=[Depends(agent_auth)])
def get_answer(rid: str, control: Control = Depends(get_control)) -> dict:
    req = control.store.get(rid)
    if not req:
        raise HTTPException(status_code=404, detail="not found")
    return req.public()


@router.get("/status", dependencies=[Depends(agent_auth)])
def status(control: Control = Depends(get_control)) -> dict:
    return control.status()


@router.post("/tick", dependencies=[Depends(agent_auth)])
def tick(control: Control = Depends(get_control)) -> dict:
    return {"done": control.tick()}


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, control: Control = Depends(get_control),
                           x_telegram_bot_api_secret_token: str = Header(default="")) -> dict:
    if not _same(x_telegram_bot_api_secret_token, os.getenv("TELEGRAM_WEBHOOK_SECRET", "")):
        raise HTTPException(status_code=401, detail="unauthorized")
    if control.tg is None:
        raise HTTPException(status_code=503, detail="telegram not configured")
    control.handle_update(await request.json())
    return {"ok": True}


async def _twilio_form(request: Request) -> dict[str, str]:
    form = {k: str(v) for k, v in (await request.form()).items()}
    url = voice.public_url(request.url.path)
    if not voice.valid_signature(url, form, request.headers.get("x-twilio-signature", "")):
        raise HTTPException(status_code=403, detail="bad signature")
    return form


def _xml(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


@router.post("/voice/twiml/{rid}")
async def voice_twiml(rid: str, request: Request, control: Control = Depends(get_control)) -> Response:
    await _twilio_form(request)
    req = control.store.get(rid)
    if not req or req.status != "open":
        return _xml(voice.reply_twiml("השאלה כבר נסגרה. תודה."))
    return _xml(voice.call_twiml(req))


@router.post("/voice/gather/{rid}")
async def voice_gather(rid: str, request: Request, control: Control = Depends(get_control)) -> Response:
    form = await _twilio_form(request)
    req = control.store.get(rid)
    if not req or req.status != "open":
        return _xml(voice.reply_twiml("השאלה כבר נסגרה. תודה."))
    answer, say = voice.gather_result(req, form.get("Digits", ""))
    if answer:
        control.record(req, answer, "phone")
    return _xml(voice.reply_twiml(say))
