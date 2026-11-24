"""The world-agent contract (v0), ESH27.

One file, no dependencies. It defines:
  * what an agent sees (Observation) and what it may do (Action),
  * how work becomes a Measurement,
  * the Verifier: the only party that can credit CRD,
  * the Ledger: append-only, hash-chained, checkable by anyone.

Core rule: CRD is paid only for verified work.
  - A job with a computable answer (e.g. a photo-street check) is verified against that answer.
  - A job without one (e.g. a building's floor count) is confirmed only when at least
    two INDEPENDENT measurements agree within tolerance. Two agents of the same operator,
    or on the same device, are not independent. This is the sybil rule.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import statistics
import time
from dataclasses import dataclass, field, asdict
from typing import Any

CONTRACT_VERSION = "0.2"

# ---- earning and spending (input for the crypto lab's tokenomics) ----
EARN = {
    "computed_check": 1,     # answer matches the computed answer (photo or street check)
    "floors_confirmed": 5,   # one of >=2 independent agreeing measurements
}
SPEND = {
    "brain_call": 1,         # one decision by a model brain (rule brain is free)
    "build": 10,             # a structure on the agent's own plot (after the freeze)
}
FREE_BRAIN_CALLS_PER_DAY = 20  # crypto lab note 3: model calls are free up to a daily quota, then cost 1
FLOORS_TOL = 1               # agree = within +-1 floor
MIN_INDEPENDENT = 2

ACTION_KINDS = ("walk", "work", "rest")
# jobs whose answer is computable from the map, and their allowed answers
COMPUTED = {
    "photo_check": ("consistent", "inconsistent", "no_street"),
    "street_check": ("found", "not_found"),
}


def job_kind(job: dict) -> str:
    """city_v0 jobs use kind photo/commons; contract jobs use job_kind."""
    if "job_kind" in job:
        return job["job_kind"]
    return {"photo": "photo_check", "commons": "street_check"}.get(job.get("kind"), job.get("kind", ""))


PUBLIC_FIELDS = ("id", "kind", "job_kind", "node", "x", "y", "street", "r", "d_street", "n_cand", "n_nodes", "what")


def public_job(job: dict) -> dict:
    """What an agent may see of a job: never the verdict or anything derived from the answer."""
    return {k: job[k] for k in PUBLIC_FIELDS if k in job}


def truth(job: dict) -> str:
    """The computed answer for a COMPUTED job (from the map, by build_city.py)."""
    v = job.get("verdict", "")
    k = job_kind(job)
    if k == "photo_check":
        if v == "consistent":
            return "consistent"
        if "no street" in v or v == "no_street":
            return "no_street"
        return "inconsistent"
    if k == "street_check":
        return "found" if v in ("street found", "found") else "not_found"
    raise ContractError(f"no computed truth for {k!r}")


class ContractError(ValueError):
    pass


@dataclass
class Observation:
    agent_id: str
    operator_id: str
    tick: int
    node: int
    pos: tuple[float, float]
    plot: str | None
    credits: int
    jobs: list[dict] = field(default_factory=list)  # open jobs near the agent, data only

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Action:
    kind: str
    to_node: int | None = None
    job_id: str | None = None
    answer: dict | None = None

    def validate(self) -> "Action":
        if self.kind not in ACTION_KINDS:
            raise ContractError(f"unknown action kind: {self.kind!r}")
        if self.kind == "walk" and not isinstance(self.to_node, int):
            raise ContractError("walk needs an integer to_node")
        if self.kind == "work":
            if not self.job_id or not isinstance(self.answer, dict):
                raise ContractError("work needs job_id and an answer dict")
        return self

    @staticmethod
    def from_dict(d: Any) -> "Action":
        if not isinstance(d, dict):
            raise ContractError("action must be a JSON object")
        allowed = {"kind", "to_node", "job_id", "answer"}
        extra = set(d) - allowed
        if extra:
            raise ContractError(f"unknown action fields: {sorted(extra)}")
        return Action(**d).validate()


@dataclass
class Measurement:
    job_id: str
    job_kind: str
    agent_id: str
    operator_id: str
    device: str
    value: Any
    t: float = field(default_factory=time.time)
    sig: str = ""

    def payload(self) -> bytes:
        return _canon({"job": self.job_id, "agent": self.agent_id, "op": self.operator_id,
                       "dev": self.device, "value": self.value})


class OperatorRegistry:
    """Crypto lab note 1: operator and device must come from a registered, signed identity,
    not from what the agent claims. Each operator holds a key; each device is registered to one operator."""

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}
        self._dev: dict[str, str] = {}
        self.internal: set[str] = set()   # test operators, labelled internal (note 4)

    def register(self, operator_id: str, key: bytes, devices: list[str], internal: bool = False) -> None:
        self._keys[operator_id] = key
        for d in devices:
            if self._dev.get(d, operator_id) != operator_id:
                raise ContractError(f"device {d} already belongs to another operator")
            self._dev[d] = operator_id
        if internal:
            self.internal.add(operator_id)

    def sign(self, m: "Measurement", key: bytes) -> "Measurement":
        m.sig = hmac.new(key, m.payload(), hashlib.sha256).hexdigest()
        return m

    def check(self, m: "Measurement") -> str | None:
        key = self._keys.get(m.operator_id)
        if key is None:
            return "unknown operator"
        if self._dev.get(m.device) != m.operator_id:
            return "device not registered to this operator"
        good = hmac.new(key, m.payload(), hashlib.sha256).hexdigest()
        if not m.sig or not hmac.compare_digest(good, m.sig):
            return "bad signature"
        return None


# ---------------------------------------------------------------- ledger
def _canon(obj: dict) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


class Ledger:
    """Append-only, hash-chained. Each entry carries the hash of the one before it."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self.entries: list[dict] = []

    @property
    def head(self) -> str:
        return self.entries[-1]["hash"] if self.entries else self.GENESIS

    def _append(self, kind: str, agent: str, amount: int, ref: str, note: str = "") -> dict:
        e = {"seq": len(self.entries), "kind": kind, "agent": agent, "amount": amount,
             "ref": ref, "note": note, "prev": self.head}
        e["hash"] = hashlib.sha256(_canon(e)).hexdigest()
        self.entries.append(e)
        return e

    def balance(self, agent: str) -> int:
        return sum(e["amount"] for e in self.entries if e["agent"] == agent)

    def verify(self) -> bool:
        prev = self.GENESIS
        for i, e in enumerate(self.entries):
            body = {k: v for k, v in e.items() if k != "hash"}
            if e["seq"] != i or e["prev"] != prev:
                return False
            if hashlib.sha256(_canon(body)).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True

    def anchor(self) -> dict:
        """Crypto lab note 2: publish this outside the writer's control (e.g. commit it to a repo)."""
        return {"seq": len(self.entries) - 1, "head": self.head, "contract": CONTRACT_VERSION}

    def dump(self) -> str:
        return "\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in self.entries)


# ---------------------------------------------------------------- verifier
def independent(a: Measurement, b: Measurement) -> bool:
    return a.operator_id != b.operator_id and a.device != b.device


class Verifier:
    """The only writer of CRD. Agents hand in measurements; they never touch balances."""

    def __init__(self, jobs: dict[str, dict], ledger: Ledger | None = None,
                 registry: OperatorRegistry | None = None) -> None:
        self.jobs = jobs
        self.registry = registry
        self.free_used: dict[tuple[str, int], int] = {}
        self.ledger = ledger or Ledger()
        self.pending: dict[str, list[Measurement]] = {}
        self.confirmed: dict[str, dict] = {}
        self.paid: set[tuple[str, str]] = set()   # (job_id, agent_id)

    def submit(self, m: Measurement) -> dict:
        job = self.jobs.get(m.job_id)
        if job is None:
            return {"ok": False, "reason": "unknown job"}
        if (m.job_id, m.agent_id) in self.paid:
            return {"ok": False, "reason": "already paid for this job"}
        kind = job_kind(job)
        if kind in COMPUTED:
            got = m.value.get("verdict") if isinstance(m.value, dict) else None
            if got not in COMPUTED[kind]:
                return {"ok": False, "reason": "bad verdict"}
            if got == truth(job):
                self.paid.add((m.job_id, m.agent_id))
                e = self.ledger._append("earn", m.agent_id, EARN["computed_check"], m.job_id, kind)
                return {"ok": True, "paid": EARN["computed_check"], "entry": e["seq"]}
            return {"ok": True, "paid": 0, "reason": "wrong answer"}
        if kind == "floors":
            return self._submit_floors(m)
        return {"ok": False, "reason": f"unsupported job kind {kind!r}"}

    def _submit_floors(self, m: Measurement) -> dict:
        # independence rests on identity, so floors are only accepted from signed, registered operators
        if self.registry is None:
            return {"ok": False, "reason": "floors need an operator registry"}
        why = self.registry.check(m)
        if why:
            return {"ok": False, "reason": why}
        if not isinstance(m.value, int) or not (1 <= m.value <= 80):
            return {"ok": False, "reason": "floors must be an int 1..80"}
        if m.job_id in self.confirmed:
            c = self.confirmed[m.job_id]
            if abs(m.value - c["floors"]) <= FLOORS_TOL and all(independent(m, p) for p in c["by"]):
                c["by"].append(m)
                self.paid.add((m.job_id, m.agent_id))
                self.ledger._append("earn", m.agent_id, EARN["floors_confirmed"], m.job_id, "floors late confirm")
                return {"ok": True, "paid": EARN["floors_confirmed"], "state": "confirmed"}
            return {"ok": True, "paid": 0, "state": "confirmed", "reason": "disagrees or not independent"}
        bucket = self.pending.setdefault(m.job_id, [])
        bucket.append(m)
        # largest group of mutually independent measurements that agree within tolerance
        best: list[Measurement] = []
        for anchor in bucket:
            group = [anchor]
            for other in bucket:
                if other is anchor:
                    continue
                if abs(other.value - anchor.value) <= FLOORS_TOL and all(independent(other, g) for g in group):
                    group.append(other)
            if len(group) > len(best):
                best = group
        if len(best) >= MIN_INDEPENDENT:
            floors = round(statistics.median(g.value for g in best))
            sigma = statistics.pstdev([g.value for g in best])
            self.confirmed[m.job_id] = {"floors": floors, "sigma": round(sigma, 2), "n": len(best), "by": best}
            for g in best:
                self.paid.add((m.job_id, g.agent_id))
                self.ledger._append("earn", g.agent_id, EARN["floors_confirmed"], m.job_id, "floors confirmed")
            del self.pending[m.job_id]
            return {"ok": True, "paid": EARN["floors_confirmed"] if m in best else 0, "state": "confirmed",
                    "floors": floors, "n": len(best)}
        return {"ok": True, "paid": 0, "state": "pending", "n": len(bucket)}

    def spend(self, agent: str, what: str, ref: str = "", day: int = 0) -> dict:
        if what == "brain_call":
            used = self.free_used.get((agent, day), 0)
            if used < FREE_BRAIN_CALLS_PER_DAY:
                self.free_used[(agent, day)] = used + 1
                return {"ok": True, "spent": 0, "free_left": FREE_BRAIN_CALLS_PER_DAY - used - 1}
        cost = SPEND.get(what)
        if cost is None:
            return {"ok": False, "reason": "unknown spend"}
        if self.ledger.balance(agent) < cost:
            return {"ok": False, "reason": "insufficient CRD"}
        e = self.ledger._append("spend", agent, -cost, ref or what, what)
        return {"ok": True, "spent": cost, "entry": e["seq"]}


def dist(a, b) -> float:
    return math.dist(a, b)
