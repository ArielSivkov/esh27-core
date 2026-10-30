"""
CrownBot control center: agents ask Ariel, Telegram answers, a phone call escalates.

- store.py       HITL requests and the stop switch (SQLite)
- escalation.py  when to remind, call or give up (pure, no I/O)
- telegram.py    Bot API client and message layout
- voice.py       Twilio call + TwiML, off until TWILIO_* is set
- router.py      HTTP endpoints: /control/ask, /control/telegram/webhook, /control/tick, /control/voice/*
"""
