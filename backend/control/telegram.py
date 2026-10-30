"""
Telegram Bot API client for CrownBot and the layout of HITL messages.

Env: TELEGRAM_BOT_TOKEN (from BotFather), TELEGRAM_ADMIN_CHAT_ID (Ariel's numeric user id).
Only that user may press buttons or send commands; everyone else is ignored.
"""

from __future__ import annotations

import html
import logging
import os

import httpx

from backend.control.store import Request

logger = logging.getLogger("esh27-core.control.telegram")

URGENCY_LABEL = {"info": "ℹ️ לידיעה", "normal": "🟡 שאלה", "blocking": "🔴 חוסם עבודה"}


def admin_id() -> int | None:
    v = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    return int(v) if v.lstrip("-").isdigit() else None


def configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN")) and admin_id() is not None


def render(req: Request, note: str = "") -> str:
    lines = [f"<b>{URGENCY_LABEL[req.urgency]}</b> · {html.escape(req.agent)} · <code>{req.id}</code>",
             "", html.escape(req.question)]
    if req.sensitive:
        lines += ["", "🔐 פעולה רגישה: אחרי הבחירה תתבקש לאשר שוב."]
    if req.status == "answered":
        via = "בטלפון" if req.answered_via == "phone" else "בטלגרם"
        lines += ["", f"✅ נענה {via}: <b>{html.escape(req.answer or '')}</b>"]
    elif req.status == "expired":
        lines += ["", "⌛ לא נענה בזמן. הסוכן לא יבצע את הפעולה."]
    elif req.status == "cancelled":
        lines += ["", "🚫 בוטל"]
    else:
        lines += ["", "אפשר גם להשיב בטקסט חופשי (Reply להודעה הזו)."]
    if note:
        lines += ["", note]
    return "\n".join(lines)


def keyboard(req: Request) -> dict | None:
    if req.status != "open":
        return None
    row = [{"text": opt, "callback_data": f"a:{req.id}:{i}"} for i, opt in enumerate(req.options)]
    return {"inline_keyboard": [row]}


def confirm_keyboard(req: Request, choice: int) -> dict:
    return {"inline_keyboard": [[
        {"text": f"✔️ כן, סופי: {req.options[choice]}", "callback_data": f"c:{req.id}:{choice}"},
        {"text": "↩️ חזרה", "callback_data": f"b:{req.id}:0"},
    ]]}


class Telegram:
    def __init__(self, token: str | None = None, client: httpx.Client | None = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.client = client or httpx.Client(timeout=10)

    def call(self, method: str, **payload) -> dict:
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        r = self.client.post(f"https://api.telegram.org/bot{self.token}/{method}", json=payload)
        data = r.json()
        if not data.get("ok"):
            # The token is part of the URL; never log the URL.
            logger.warning("telegram %s failed: %s", method, data.get("description"))
        return data

    def send(self, chat_id: int, text: str, markup: dict | None = None, silent: bool = False,
             reply_to: int | None = None) -> int | None:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_notification": silent}
        if markup:
            payload["reply_markup"] = markup
        if reply_to:
            payload["reply_parameters"] = {"message_id": reply_to}
        res = self.call("sendMessage", **payload)
        return (res.get("result") or {}).get("message_id")

    def edit(self, chat_id: int, message_id: int, text: str, markup: dict | None = None) -> None:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
        payload["reply_markup"] = markup or {"inline_keyboard": []}
        self.call("editMessageText", **payload)

    def ack(self, callback_id: str, text: str = "") -> None:
        self.call("answerCallbackQuery", callback_query_id=callback_id, text=text)
