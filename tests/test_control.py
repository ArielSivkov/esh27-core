"""Control center: escalation ladder, Telegram flow, phone, HTTP auth. No network.

Run: python -m unittest discover -s tests
"""

import os
import tempfile
import unittest
from datetime import datetime

from backend.control import escalation, voice
from backend.control.escalation import TZ
from backend.control.service import Control, Paused
from backend.control.store import Store

ADMIN = 555
# Tuesday 10:00 Jerusalem: not night, not Shabbat.
T0 = datetime(2026, 11, 3, 10, 0, tzinfo=TZ).timestamp()
MIN = 60


class FakeTelegram:
    def __init__(self):
        self.sent, self.edits, self.acks, self._mid = [], [], [], 100

    def send(self, chat_id, text, markup=None, silent=False, reply_to=None):
        self._mid += 1
        self.sent.append({"chat": chat_id, "text": text, "markup": markup, "silent": silent, "id": self._mid})
        return self._mid

    def edit(self, chat_id, message_id, text, markup=None):
        self.edits.append({"id": message_id, "text": text, "markup": markup})

    def ack(self, callback_id, text=""):
        self.acks.append(text)


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def make(caller=None):
    os.environ["TELEGRAM_ADMIN_CHAT_ID"] = str(ADMIN)
    db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    clock, calls = Clock(T0), []
    c = Control(store=Store(db), tg=FakeTelegram(), clock=clock,
                caller=caller if caller is not None else (lambda req: calls.append(req.id) or "CA1"))
    return c, clock, calls


def button(c, data, user=ADMIN):
    c.handle_update({"callback_query": {"id": "q", "from": {"id": user}, "data": data}})


def text(c, body, user=ADMIN, reply_to=None):
    msg = {"from": {"id": user}, "text": body}
    if reply_to:
        msg["reply_to_message"] = {"message_id": reply_to}
    c.handle_update({"message": msg})


class EscalationTest(unittest.TestCase):
    def test_blocking_ladder(self):
        c, clock, calls = make()
        req = c.ask("night-shift", "להעלות את הלוח לאתר?", urgency="blocking")
        steps = []
        for minute in (4, 5, 6, 10, 11, 25, 59, 60):
            clock.t = T0 + minute * MIN
            steps.append((minute, c.tick()))
        self.assertEqual([s for s in steps if s[1]],
                         [(5, [(req.id, "remind")]), (10, [(req.id, "call")]),
                          (25, [(req.id, "call")]), (60, [(req.id, "expire")])])
        self.assertEqual(calls, [req.id, req.id])
        self.assertEqual(c.store.get(req.id).status, "expired")
        self.assertIn("לא נענה בזמן", c.tg.edits[-1]["text"])

    def test_normal_never_calls(self):
        c, clock, calls = make()
        c.ask("a", "q?")
        for minute in range(0, 120, 5):
            clock.t = T0 + minute * MIN
            c.tick()
        self.assertEqual(calls, [])

    def test_quiet_on_shabbat_and_no_calls_at_night(self):
        c, _, _ = make()
        req = c.ask("a", "q?", urgency="blocking")
        friday = datetime(2026, 11, 6, 16, 0, tzinfo=TZ).timestamp()
        req.created_at = friday - 30 * MIN
        self.assertIsNone(escalation.next_step(req, friday))
        night = datetime(2026, 11, 3, 2, 0, tzinfo=TZ).timestamp()
        req.created_at = night - 11 * MIN
        self.assertEqual(escalation.next_step(req, night), "remind")
        req.reminders = 1
        self.assertIsNone(escalation.next_step(req, night))

    def test_no_phone_configured_tells_telegram(self):
        c, clock, _ = make(caller=False)
        c.caller = None
        req = c.ask("a", "q?", urgency="blocking")
        clock.t = T0 + 10 * MIN
        self.assertEqual(c.tick(), [(req.id, "call-skipped")])
        self.assertIn("עוד לא מוגדרות", c.tg.sent[-1]["text"])


class TelegramFlowTest(unittest.TestCase):
    def test_button_answers_once(self):
        c, _, _ = make()
        req = c.ask("a", "לשלוח?", ["כן", "לא"])
        button(c, f"a:{req.id}:1")
        self.assertEqual((c.store.get(req.id).answer, c.store.get(req.id).answered_via), ("לא", "telegram"))
        button(c, f"a:{req.id}:0")
        self.assertEqual(c.store.get(req.id).answer, "לא")
        self.assertEqual(c.tg.acks[-1], "השאלה כבר סגורה")

    def test_strangers_are_ignored(self):
        c, _, _ = make()
        req = c.ask("a", "q?")
        button(c, f"a:{req.id}:0", user=999)
        text(c, "/stop", user=999)
        self.assertEqual(c.store.get(req.id).status, "open")
        self.assertFalse(c.store.paused)

    def test_sensitive_needs_second_click(self):
        c, _, _ = make()
        req = c.ask("a", "לשלם 167$ על האחסון?", sensitive=True)
        button(c, f"a:{req.id}:0")
        self.assertEqual(c.store.get(req.id).status, "open")
        self.assertIn("c:", c.tg.edits[-1]["markup"]["inline_keyboard"][0][0]["callback_data"])
        text(c, "כן", reply_to=req.telegram_message_id or c.store.get(req.id).telegram_message_id)
        self.assertEqual(c.store.get(req.id).status, "open")
        button(c, f"c:{req.id}:0")
        self.assertEqual(c.store.get(req.id).answer, "כן")

    def test_free_text_reply(self):
        c, _, _ = make()
        req = c.ask("a", "איזו שכונה קודם?", ["תלפיות", "גילה"])
        text(c, "קודם בית צפאפא", reply_to=c.store.get(req.id).telegram_message_id)
        self.assertEqual(c.store.get(req.id).answer, "קודם בית צפאפא")

    def test_stop_and_resume(self):
        c, _, _ = make()
        text(c, "/stop")
        with self.assertRaises(Paused):
            c.ask("a", "q?")
        text(c, "/resume")
        self.assertEqual(c.ask("a", "q?").status, "open")

    def test_question_is_escaped(self):
        c, _, _ = make()
        c.ask("<b>x</b>", "a < b & c")
        self.assertIn("a &lt; b &amp; c", c.tg.sent[-1]["text"])
        self.assertIn("&lt;b&gt;x", c.tg.sent[-1]["text"])


class VoiceTest(unittest.TestCase):
    def test_signature(self):
        url, params = "https://x.example/control/voice/gather/ab", {"Digits": "1", "CallSid": "CA1"}
        import base64, hashlib, hmac
        good = base64.b64encode(hmac.new(b"tok", (url + "CallSidCA1Digits1").encode(), hashlib.sha1).digest()).decode()
        self.assertTrue(voice.valid_signature(url, params, good, token="tok"))
        self.assertFalse(voice.valid_signature(url, params, good, token="other"))
        self.assertFalse(voice.valid_signature(url, params, "", token="tok"))

    def test_keys_and_sensitive(self):
        c, _, _ = make()
        req = c.ask("a", "q?", ["כן", "לא"])
        self.assertEqual(voice.gather_result(req, "2")[0], "לא")
        self.assertIsNone(voice.gather_result(req, "3")[0])
        sens = c.ask("a", "לשלם?", sensitive=True)
        self.assertIsNone(voice.gather_result(sens, "1")[0])
        self.assertNotIn("<Gather", voice.call_twiml(sens))
        self.assertIn("<Gather", voice.call_twiml(req))


class HttpTest(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from backend.api import main
        from backend.control import router
        self.c, _, _ = make()
        main.app.dependency_overrides[router.get_control] = lambda: self.c
        os.environ.update(CONTROL_TOKEN="agent-secret", TELEGRAM_WEBHOOK_SECRET="hook-secret")
        self.http = TestClient(main.app)
        self.addCleanup(main.app.dependency_overrides.clear)

    def test_ask_requires_token(self):
        body = {"agent": "a", "question": "q?"}
        self.assertEqual(self.http.post("/control/ask", json=body).status_code, 401)
        r = self.http.post("/control/ask", json=body, headers={"Authorization": "Bearer agent-secret"})
        self.assertEqual(r.status_code, 200)
        rid = r.json()["id"]
        got = self.http.get(f"/control/ask/{rid}", headers={"Authorization": "Bearer agent-secret"})
        self.assertEqual(got.json()["status"], "open")

    def test_webhook_requires_secret(self):
        upd = {"message": {"from": {"id": ADMIN}, "text": "/stop"}}
        self.assertEqual(self.http.post("/control/telegram/webhook", json=upd).status_code, 401)
        r = self.http.post("/control/telegram/webhook", json=upd,
                           headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.c.store.paused)
        r = self.http.post("/control/ask", json={"agent": "a", "question": "q?"},
                           headers={"Authorization": "Bearer agent-secret"})
        self.assertEqual(r.status_code, 423)

    def test_twilio_requires_signature(self):
        self.assertEqual(self.http.post("/control/voice/gather/x", data={"Digits": "1"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
