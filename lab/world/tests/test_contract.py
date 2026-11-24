import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "contract"))
from world_contract import (Action, ContractError, Ledger, Measurement, Verifier, EARN,  # noqa: E402
                            job_kind, truth)

CITY = os.path.join(HERE, "..", "data", "city_v0.json")


def m(job, agent, op, dev, value):
    return Measurement(job_id=job, job_kind="", agent_id=agent, operator_id=op, device=dev, value=value)


# ---------------- actions
def test_action_validation():
    Action.from_dict({"kind": "walk", "to_node": 5})
    Action.from_dict({"kind": "work", "job_id": "001", "answer": {"verdict": "consistent"}})
    for bad in [{"kind": "fly"}, {"kind": "walk"}, {"kind": "work", "job_id": "x"},
                {"kind": "rest", "transfer": 100}, "rest", None]:
        with pytest.raises(ContractError):
            Action.from_dict(bad)


# ---------------- ledger
def test_ledger_chain_detects_tampering():
    L = Ledger()
    L._append("earn", "a1", 5, "j1")
    L._append("earn", "a2", 5, "j1")
    L._append("spend", "a1", -1, "brain_call")
    assert L.verify() and L.balance("a1") == 4
    L.entries[0]["amount"] = 500
    assert not L.verify()


def test_ledger_detects_removed_entry():
    L = Ledger()
    for i in range(3):
        L._append("earn", "a", 1, f"j{i}")
    del L.entries[1]
    assert not L.verify()


# ---------------- computed jobs on the real city data
def test_real_city_jobs_have_truth():
    d = json.load(open(CITY))
    kinds = {job_kind(j) for j in d["jobs"]}
    assert kinds == {"photo_check", "street_check"}
    for j in d["jobs"]:
        truth(j)  # never raises on the real data


def test_computed_job_pays_only_correct_answer_once():
    jobs = {"001": {"kind": "photo", "verdict": "consistent"}}
    V = Verifier(jobs)
    assert V.submit(m("001", "a1", "op1", "d1", {"verdict": "inconsistent"}))["paid"] == 0
    assert V.submit(m("001", "a1", "op1", "d1", {"verdict": "consistent"}))["paid"] == EARN["computed_check"]
    assert V.submit(m("001", "a1", "op1", "d1", {"verdict": "consistent"}))["ok"] is False  # no double pay
    assert V.submit(m("001", "a1", "op1", "d1", {"verdict": "maybe"}))["ok"] is False


# ---------------- floors: the n>=2 independent rule
FL = {"B1": {"job_kind": "floors"}}


def test_floors_need_two_independent():
    V = Verifier(dict(FL))
    r1 = V.submit(m("B1", "a1", "op1", "d1", 8))
    assert r1["state"] == "pending" and r1["paid"] == 0
    r2 = V.submit(m("B1", "a2", "op2", "d2", 9))
    assert r2["state"] == "confirmed" and V.confirmed["B1"]["n"] == 2
    assert V.ledger.balance("a1") == V.ledger.balance("a2") == EARN["floors_confirmed"]
    assert V.ledger.verify()


def test_sybil_same_operator_never_confirms():
    V = Verifier(dict(FL))
    for i in range(10):  # one operator, ten fake agents, ten devices
        V.submit(m("B1", f"s{i}", "attacker", f"dev{i}", 30))
    assert "B1" not in V.confirmed
    assert V.ledger.entries == []


def test_sybil_same_device_never_confirms():
    V = Verifier(dict(FL))
    for i in range(5):
        V.submit(m("B1", f"s{i}", f"op{i}", "one-phone", 30))
    assert "B1" not in V.confirmed


def test_disagreement_stays_pending():
    V = Verifier(dict(FL))
    V.submit(m("B1", "a1", "op1", "d1", 4))
    r = V.submit(m("B1", "a2", "op2", "d2", 8))
    assert r["state"] == "pending"


def test_late_confirmer_paid_outlier_not():
    V = Verifier(dict(FL))
    V.submit(m("B1", "a1", "op1", "d1", 8))
    V.submit(m("B1", "a2", "op2", "d2", 8))
    assert V.submit(m("B1", "a3", "op3", "d3", 9))["paid"] == EARN["floors_confirmed"]
    assert V.submit(m("B1", "a4", "op4", "d4", 20))["paid"] == 0
    assert V.submit(m("B1", "a5", "op1", "d5", 8))["paid"] == 0  # op1 already counted


def test_floors_value_bounds():
    V = Verifier(dict(FL))
    for bad in [0, 81, "8", 8.5, None]:
        assert V.submit(m("B1", "a1", "op1", "d1", bad))["ok"] is False


def test_spend_needs_balance():
    V = Verifier({"001": {"kind": "photo", "verdict": "consistent"}})
    assert V.spend("a1", "brain_call")["ok"] is False
    V.submit(m("001", "a1", "op1", "d1", {"verdict": "consistent"}))
    assert V.spend("a1", "brain_call")["ok"] is True
    assert V.ledger.balance("a1") == 0
    assert V.spend("a1", "teleport")["ok"] is False
