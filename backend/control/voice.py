"""
Phone escalation through Twilio. Off until TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
TWILIO_FROM and CONTROL_PHONE are all set (opening a Twilio account is Ariel's call).

The call reads the question and waits for one key: 1 approves the first option,
2 the second, 3 means "I'll answer later" and leaves the request open in Telegram.
Sensitive requests are never approved by phone; the call only says to open Telegram.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from xml.sax.saxutils import escape

import httpx

from backend.control.store import Request

VOICE = os.getenv("TWILIO_VOICE", "Google.he-IL-Standard-A")


def configured() -> bool:
    return all(os.getenv(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM",
                                       "CONTROL_PHONE", "CONTROL_PUBLIC_URL"))


def public_url(path: str) -> str:
    return os.getenv("CONTROL_PUBLIC_URL", "").rstrip("/") + path


def _say(text: str) -> str:
    return f'<Say language="he-IL" voice="{escape(VOICE)}">{escape(text)}</Say>'


def call_twiml(req: Request) -> str:
    intro = f"שלום אריאל. הסוכן {req.agent} צריך אותך. {req.question}"
    if req.sensitive or len(req.options) < 2:
        return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response>{_say(intro)}" \
               f"{_say('זו החלטה שמאשרים רק בטלגרם. פתח את הבוט.')}</Response>"
    menu = f"לחץ 1 עבור {req.options[0]}. לחץ 2 עבור {req.options[1]}. לחץ 3 כדי לענות אחר כך בטלגרם."
    action = escape(public_url(f"/control/voice/gather/{req.id}"))
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response>"
            f'<Gather numDigits="1" timeout="8" action="{action}" method="POST">'
            f"{_say(intro)}{_say(menu)}</Gather>"
            f"{_say('לא התקבלה בחירה. השאלה מחכה לך בטלגרם.')}</Response>")


def gather_result(req: Request, digit: str) -> tuple[str | None, str]:
    """Map a key press to (answer or None, what to say back)."""
    if req.sensitive:
        return None, "זו החלטה שמאשרים רק בטלגרם."
    if digit in ("1", "2") and len(req.options) >= int(digit):
        choice = req.options[int(digit) - 1]
        return choice, f"נרשם: {choice}. תודה."
    return None, "בסדר. השאלה מחכה לך בטלגרם."


def reply_twiml(text: str) -> str:
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response>{_say(text)}</Response>"


def place_call(req: Request, client: httpx.Client | None = None) -> str:
    sid, token = os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
    client = client or httpx.Client(timeout=15)
    r = client.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json", auth=(sid, token), data={
        "To": os.environ["CONTROL_PHONE"], "From": os.environ["TWILIO_FROM"],
        "Url": public_url(f"/control/voice/twiml/{req.id}"), "Method": "POST", "Timeout": "25",
    })
    r.raise_for_status()
    return r.json().get("sid", "")


def valid_signature(url: str, params: dict[str, str], signature: str, token: str | None = None) -> bool:
    """Twilio request validation: base64(HMAC-SHA1(token, url + sorted key+value pairs))."""
    token = token or os.getenv("TWILIO_AUTH_TOKEN", "")
    if not token or not signature:
        return False
    data = url + "".join(k + params[k] for k in sorted(params))
    digest = base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(digest, signature)
