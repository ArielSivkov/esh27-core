"""Append-only JSONL result ledger.

Every attempt, success or failure, is one line. Lines are never edited; a
correction is a new entry with `supersedes` pointing at the old `attempt_id`.
Each entry carries the SHA-256 of the previous line (hash chain) so silent
edits are detectable with `verify_chain()`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path


class ClaimLevel(IntEnum):
    L0_IDEA = 0             # conjecture / heuristic / analogy
    L1_NUMERIC = 1          # numerical / computational evidence, reproducible script
    L2_INFORMAL = 2         # informal proof written, not machine-checked
    L3_LEAN_VERIFIED = 3    # Lean kernel (or DRAT/exact-arith certificate) accepted
    L4_PUBLISHED = 4        # peer-reviewed or accepted by the community


@dataclass
class Certificate:
    kind: str                 # "lean" | "drat" | "exact-arith" | "sdp-rational" | "none"
    path: str = ""            # artifact path (repo-relative)
    checker: str = ""         # e.g. "lake build", "drat-trim", "sage exact check"
    checker_version: str = ""
    sha256: str = ""
    verified: bool = False


@dataclass
class Attempt:
    goal_id: str
    agent: str
    method: str                       # e.g. "lit-review", "lean-proof-search", "sat", "evo-search"
    claim_level: int = ClaimLevel.L0_IDEA
    summary: str = ""
    outcome: str = "pending"          # pending | success | partial | failed | refuted
    artifacts: list[str] = field(default_factory=list)
    certificate: dict | None = None
    model: str = ""
    dry_run: bool = False
    supersedes: str | None = None
    attempt_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def _sha(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _last_line(path: Path) -> str | None:
    if not path.exists():
        return None
    last = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line.rstrip("\n")
    return last


def validate(attempt: Attempt) -> None:
    """Enforce the honesty rule: L3+ requires a verified certificate."""
    level = int(attempt.claim_level)
    if level >= ClaimLevel.L3_LEAN_VERIFIED:
        cert = attempt.certificate or {}
        if not cert.get("verified"):
            raise ValueError(f"claim level L{level} requires a verified certificate")
        if cert.get("kind") in (None, "", "none"):
            raise ValueError("L3+ certificate must name its kind (lean/drat/exact-arith/...)")


def append(attempt: Attempt, path: str | Path) -> dict:
    path = Path(path)
    validate(attempt)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = asdict(attempt)
    rec["claim_level"] = int(attempt.claim_level)
    prev = _last_line(path)
    rec["prev_sha256"] = _sha(prev) if prev else None
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return rec


def read(path: str | Path, goal_id: str | None = None) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                if goal_id is None or rec.get("goal_id") == goal_id:
                    out.append(rec)
    return out


def verify_chain(path: str | Path) -> bool:
    path = Path(path)
    if not path.exists():
        return True
    prev = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("prev_sha256") != (_sha(prev) if prev else None):
                return False
            prev = line
    return True


def best_level(path: str | Path, goal_id: str) -> int:
    recs = [r for r in read(path, goal_id) if not r.get("dry_run")]
    return max((r.get("claim_level", 0) for r in recs), default=-1)
