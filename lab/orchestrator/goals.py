"""Load the goal bank (data/goals.csv) and rank goals.

The CSV is written by other agents, so parsing is tolerant: numeric fields may
be numbers (0-1, 1-5, 1-10, 0-100) or words (low/medium/high).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field as dc_field
from pathlib import Path

COLUMNS = [
    "id", "title", "title_he", "field", "tier", "status", "statement_short",
    "why_it_matters", "ai_tractability", "formalization_readiness",
    "known_partial_results", "suggested_attack", "references", "owner_agent",
    "progress_pct", "last_update",
]

OWNER_AGENTS = {
    "search-agent", "lean-agent", "literature-agent",
    "construction-agent", "physics-agent", "analogy-agent",
}

# Statuses that take a goal out of the active queue.
CLOSED_STATUSES = {"solved", "done", "closed", "verified", "published", "archived", "l3", "l4"}

_WORDS = {
    "very low": 0.1, "low": 0.25, "medium-low": 0.4, "med": 0.5, "medium": 0.5,
    "moderate": 0.5, "medium-high": 0.65, "high": 0.8, "very high": 0.95,
}


def norm01(value: str | None, default: float = 0.3) -> float:
    """Map a heterogeneous score to [0, 1]."""
    if value is None:
        return default
    s = str(value).strip().lower().rstrip("%")
    if not s:
        return default
    if s in _WORDS:
        return _WORDS[s]
    try:
        x = float(s)
    except ValueError:
        return default
    if x < 1 and not s.isdigit():
        return max(0.0, x)  # already a fraction, e.g. "0.7"
    if x <= 5:  # the goal bank uses integer 1-5 scales
        return x / 5
    if x <= 10:
        return x / 10
    return min(x, 100) / 100


def tier_weight(tier: str | None) -> float:
    """Tier 1 = flagship, smaller tiers are 'stepping-stone' goals.

    We slightly prefer lower tiers (more tractable, faster feedback) but never zero
    out the flagship tier.
    """
    s = (tier or "").strip().lower()
    letter = {"a": 0.6, "b": 0.8, "c": 1.1, "d": 1.0, "p": 0.9}  # goal-bank tiers
    if s[:2] in {"a-", "b-", "c-", "d-", "p-"}:
        return letter[s[0]]
    s = s.lstrip("t")
    try:
        t = int(float(s))
    except ValueError:
        return 1.0
    return {1: 0.8, 2: 1.0, 3: 1.1}.get(t, 1.0)


@dataclass
class Goal:
    id: str
    title: str
    field: str = ""
    tier: str = ""
    status: str = ""
    owner_agent: str = ""
    raw: dict = dc_field(default_factory=dict, repr=False)

    @property
    def tractability(self) -> float:
        return norm01(self.raw.get("ai_tractability"))

    @property
    def readiness(self) -> float:
        return norm01(self.raw.get("formalization_readiness"))

    @property
    def progress(self) -> float:
        """progress_pct is a percentage (0-100); a value <= 1 is read as a fraction."""
        s = (self.raw.get("progress_pct") or "").strip().rstrip("%")
        try:
            x = float(s)
        except ValueError:
            return 0.0
        return max(0.0, min(1.0, x if x <= 1 else x / 100))

    @property
    def is_open(self) -> bool:
        return self.status.strip().lower() not in CLOSED_STATUSES

    def score(self) -> float:
        """Priority = tractability * readiness * tier weight * remaining work."""
        remaining = max(0.05, 1.0 - self.progress)
        return round(self.tractability * self.readiness * tier_weight(self.tier) * remaining, 4)

    def get(self, key: str, default: str = "") -> str:
        return (self.raw.get(key) or default).strip()


def load_goals(path: str | Path) -> list[Goal]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"goal bank not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in ("id", "title") if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing required columns {missing}")
        goals = []
        for row in reader:
            row = {k.strip(): (v or "") for k, v in row.items() if k}
            if not row.get("id", "").strip():
                continue
            goals.append(Goal(
                id=row["id"].strip(),
                title=row.get("title", "").strip(),
                field=row.get("field", "").strip(),
                tier=row.get("tier", "").strip(),
                status=row.get("status", "").strip(),
                owner_agent=row.get("owner_agent", "").strip(),
                raw=row,
            ))
    return goals


def rank(goals: list[Goal], include_closed: bool = False) -> list[Goal]:
    pool = goals if include_closed else [g for g in goals if g.is_open]
    return sorted(pool, key=lambda g: (-g.score(), g.id))


def pick_next(goals: list[Goal]) -> Goal | None:
    ranked = rank(goals)
    return ranked[0] if ranked else None


def find(goals: list[Goal], goal_id: str) -> Goal | None:
    gid = goal_id.strip().lower()
    return next((g for g in goals if g.id.lower() == gid), None)
