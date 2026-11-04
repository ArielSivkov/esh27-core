"""Configuration (env-var driven, no secrets in code)."""

from __future__ import annotations

import os
from pathlib import Path

LAB_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL = os.environ.get("ESH_MODEL", "claude-opus-5-5")
GOALS_CSV = Path(os.environ.get("ESH_GOALS", LAB_ROOT / "data" / "goals.csv"))
LEDGER_PATH = Path(os.environ.get("ESH_LEDGER", LAB_ROOT / "data" / "ledger.jsonl"))
LEAN_ROOT = Path(os.environ.get("ESH_LEAN_ROOT", LAB_ROOT / "lean"))
MAX_TOKENS = int(os.environ.get("ESH_MAX_TOKENS", "8000"))
