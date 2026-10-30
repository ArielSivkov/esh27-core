"""
When to nudge Ariel about an open request. Pure functions, so the ladder is testable.

Ladder (minutes since the request was created):
- info      no nudges; expires after 72 h
- normal    Telegram reminder at 5; expires after 24 h
- blocking  reminder at 5, phone call at 10 and again at 25; expires at 60, and the
            agent must then skip the action (never "no answer means yes")

No reminders or calls on Shabbat (Fri 15:00 – Sat 20:30, Jerusalem time) and no calls
at night (CONTROL_NIGHT, default 23–7). Requests do not expire inside a quiet window,
so nothing is decided while Ariel cannot answer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from backend.control.store import Request

TZ = ZoneInfo("Asia/Jerusalem")
MIN = 60.0


@dataclass(frozen=True)
class Policy:
    reminds_at: tuple[float, ...]
    calls_at: tuple[float, ...]
    expires_after: float


POLICIES = {
    "info": Policy((), (), 72 * 60 * MIN),
    "normal": Policy((5 * MIN,), (), 24 * 60 * MIN),
    "blocking": Policy((5 * MIN,), (10 * MIN, 25 * MIN), 60 * MIN),
}


def _night_hours() -> tuple[int, int]:
    start, _, end = os.getenv("CONTROL_NIGHT", "23-7").partition("-")
    return int(start), int(end)


def is_shabbat(local: datetime) -> bool:
    wd, hm = local.weekday(), (local.hour, local.minute)  # Monday=0 … Friday=4, Saturday=5
    return (wd == 4 and hm >= (15, 0)) or (wd == 5 and hm < (20, 30))


def is_night(local: datetime) -> bool:
    start, end = _night_hours()
    h = local.hour
    return h >= start or h < end if start > end else start <= h < end


def next_step(req: Request, now: float) -> str | None:
    """Return 'remind', 'call', 'expire' or None for an open request."""
    if req.status != "open":
        return None
    policy = POLICIES[req.urgency]
    age = now - req.created_at
    local = datetime.fromtimestamp(now, TZ)
    if is_shabbat(local):
        return None
    if age >= policy.expires_after:
        return "expire"
    if req.calls < len(policy.calls_at) and age >= policy.calls_at[req.calls] and not is_night(local):
        return "call"
    if req.reminders < len(policy.reminds_at) and age >= policy.reminds_at[req.reminders]:
        return "remind"
    return None
