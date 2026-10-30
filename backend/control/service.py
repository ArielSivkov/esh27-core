"""
Control-center logic shared by the HTTP router and the MCP tools.

Telegram and the phone are injected, so tests run without network.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from backend.control import escalation, telegram, voice
from backend.control.store import Request, Store, get_store

logger = logging.getLogger("esh27-core.control")

HELP = ("<b>CrownBot · מרכז שליטה</b>\n"
        "/pending – שאלות שמחכות לך\n"
        "/status – מצב המערכת\n"
        "/stop – עצירת חירום לכל הסוכנים\n"
        "/resume – חידוש עבודה")


class Paused(Exception):
    pass


class Control:
    def __init__(self, store: Store | None = None, tg: telegram.Telegram | None = None,
                 caller: Callable[[Request], str] | None = None, clock: Callable[[], float] = time.time):
        self.store = store or get_store()
        self.tg = tg if tg is not None else (telegram.Telegram() if telegram.configured() else None)
        self.caller = caller if caller is not None else (voice.place_call if voice.configured() else None)
        self.clock = clock

    @property
    def chat(self) -> int | None:
        return telegram.admin_id()

    # Agents ---------------------------------------------------------------
    def ask(self, agent: str, question: str, options: list[str] | None = None,
            urgency: str = "normal", sensitive: bool = False) -> Request:
        if self.store.paused:
            raise Paused("Ariel pressed /stop; all agents are paused")
        req = self.store.create(agent, question, options, urgency, sensitive, now=self.clock())
        if self.tg and self.chat:
            mid = self.tg.send(self.chat, telegram.render(req), telegram.keyboard(req),
                               silent=req.urgency == "info")
            if mid:
                self.store.set_message_id(req.id, mid)
        else:
            logger.warning("telegram not configured; request %s waits without a message", req.id)
        return self.store.get(req.id)

    def status(self) -> dict:
        return {"paused": self.store.paused, "open": len(self.store.open_requests()),
                "telegram": bool(self.tg and self.chat), "phone": bool(self.caller)}

    # Ariel's answers --------------------------------------------------------
    def record(self, req: Request, answer: str, via: str) -> bool:
        if not self.store.answer(req.id, answer, via, now=self.clock()):
            return False
        self._refresh(self.store.get(req.id))
        return True

    def _refresh(self, req: Request, note: str = "") -> None:
        if self.tg and self.chat and req.telegram_message_id:
            self.tg.edit(self.chat, req.telegram_message_id, telegram.render(req, note), telegram.keyboard(req))

    # Escalation -------------------------------------------------------------
    def tick(self) -> list[tuple[str, str]]:
        done = []
        for req in self.store.open_requests():
            step = escalation.next_step(req, self.clock())
            if step is None:
                continue
            if step == "expire":
                self.store.close(req.id, "expired", now=self.clock())
                self._refresh(self.store.get(req.id))
            elif step == "remind":
                self.store.note_nudge(req.id, "remind", now=self.clock())
                if self.tg and self.chat:
                    self.tg.send(self.chat, f"⏰ תזכורת: הסוכן {req.agent} מחכה לך (<code>{req.id}</code>)",
                                 reply_to=req.telegram_message_id)
            elif step == "call":
                # Count the attempt even if no phone is configured, so the ladder moves on.
                self.store.note_nudge(req.id, "call", now=self.clock())
                if self.caller:
                    try:
                        self.caller(req)
                    except Exception:  # a failed call must not stop the other requests
                        logger.exception("phone call for %s failed", req.id)
                        step = "call-failed"
                elif self.tg and self.chat:
                    self.tg.send(self.chat, f"📵 היה צריך להתקשר אליך על <code>{req.id}</code>, "
                                            "אבל שיחות טלפון עוד לא מוגדרות.", reply_to=req.telegram_message_id)
                    step = "call-skipped"
            done.append((req.id, step))
        return done

    # Telegram updates ---------------------------------------------------------
    def handle_update(self, update: dict) -> None:
        if "callback_query" in update:
            self._on_button(update["callback_query"])
        elif "message" in update:
            self._on_message(update["message"])

    def _from_admin(self, user: dict | None) -> bool:
        return bool(user) and self.chat is not None and user.get("id") == self.chat

    def _on_button(self, cq: dict) -> None:
        if not self._from_admin(cq.get("from")):
            return
        kind, rid, idx = (cq.get("data") or "x::0").split(":", 2)
        req = self.store.get(rid)
        if not req or req.status != "open" or not idx.isdigit() or int(idx) >= len(req.options):
            self.tg.ack(cq["id"], "השאלה כבר סגורה")
            return
        choice = int(idx)
        if kind == "a" and req.sensitive:
            self.tg.edit(self.chat, req.telegram_message_id, telegram.render(req),
                         telegram.confirm_keyboard(req, choice))
            self.tg.ack(cq["id"], "אשר שוב")
        elif kind == "b":
            self._refresh(req)
            self.tg.ack(cq["id"])
        elif kind in ("a", "c"):
            self.record(req, req.options[choice], "telegram")
            self.tg.ack(cq["id"], f"נרשם: {req.options[choice]}")

    def _on_message(self, msg: dict) -> None:
        if not self._from_admin(msg.get("from")):
            return
        text = (msg.get("text") or "").strip()
        cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
        if cmd in ("/start", "/help"):
            self.tg.send(self.chat, HELP)
        elif cmd == "/pending":
            open_ = self.store.open_requests()
            if not open_:
                self.tg.send(self.chat, "אין שאלות פתוחות ✅")
            for req in open_:
                mid = self.tg.send(self.chat, telegram.render(req), telegram.keyboard(req))
                if mid:
                    self.store.set_message_id(req.id, mid)
        elif cmd == "/status":
            s = self.status()
            self.tg.send(self.chat, f"מצב: {'⏸️ עצור' if s['paused'] else '▶️ פעיל'}\n"
                                    f"שאלות פתוחות: {s['open']}\n"
                                    f"שיחות טלפון: {'מוגדרות' if s['phone'] else 'לא מוגדרות'}")
        elif cmd == "/stop":
            self.store.set_flag("paused", "1")
            self.tg.send(self.chat, "⏸️ כל הסוכנים עצרו. שאלות חדשות נחסמות עד /resume.")
        elif cmd == "/resume":
            self.store.set_flag("paused", "0")
            self.tg.send(self.chat, "▶️ חזרנו לעבודה.")
        elif msg.get("reply_to_message"):
            req = self.store.by_message_id(msg["reply_to_message"].get("message_id"))
            if req and req.status == "open" and not req.sensitive:
                self.record(req, text, "telegram")
                self.tg.send(self.chat, f"נרשם עבור <code>{req.id}</code> ✅")
            elif req and req.sensitive:
                self.tg.send(self.chat, "בפעולה רגישה בוחרים בכפתורים בלבד.")
