import json
import os
import sys

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "contract"))
from world_contract import (Action, ContractError, Ledger, Measurement, Verifier, EARN,  # noqa: E402
                            OperatorRegistry, FREE_BRAIN_CALLS_PER_DAY, job_kind, truth)

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


# ---------------- floors: the n>=2 independent rule, on signed identities
FL = {"B1": {"job_kind": "floors"}}
KEYS = {f"op{i}": f"k{i}".encode() for i in range(6)}
KEYS["attacker"] = b"evil"


def reg():
    R = OperatorRegistry()
    for i in range(6):
        R.register(f"op{i}", KEYS[f"op{i}"], [f"d{i}", f"d{i}b"])
    R.register("attacker", KEYS["attacker"], [f"dev{i}" for i in range(10)])
    return R


def FV():
    return Verifier(dict(FL), registry=reg())


def sm(job, agent, op, dev, value, key=None):
    x = m(job, agent, op, dev, value)
    return OperatorRegistry().sign(x, key if key is not None else KEYS.get(op, b"?"))


def test_floors_need_two_independent():
    V = FV()
    r1 = V.submit(sm("B1", "a1", "op1", "d1", 8))
    assert r1["state"] == "pending" and r1["paid"] == 0
    r2 = V.submit(sm("B1", "a2", "op2", "d2", 9))
    assert r2["state"] == "confirmed" and V.confirmed["B1"]["n"] == 2
    assert V.ledger.balance("a1") == V.ledger.balance("a2") == EARN["floors_confirmed"]
    assert V.ledger.verify()


def test_sybil_same_operator_never_confirms():
    V = FV()
    for i in range(10):  # one operator, ten fake agents, ten devices
        V.submit(sm("B1", f"s{i}", "attacker", f"dev{i}", 30))
    assert "B1" not in V.confirmed
    assert V.ledger.entries == []


def test_sybil_same_device_never_confirms():
    V = FV()
    for i in range(5):  # five operators claiming one phone: the phone is registered to none of them
        assert V.submit(sm("B1", f"s{i}", f"op{i}", "one-phone", 30))["reason"] == "device not registered to this operator"
    assert "B1" not in V.confirmed


def test_forged_identity_rejected():
    V = FV()
    # the attacker claims to be op1 on op1's device, but cannot sign with op1's key
    r = V.submit(sm("B1", "fake", "op1", "d1", 30, key=KEYS["attacker"]))
    assert r["ok"] is False and r["reason"] == "bad signature"
    assert V.submit(sm("B1", "x", "nobody", "d1", 30))["reason"] == "unknown operator"
    unsigned = m("B1", "a1", "op1", "d1", 8)
    assert V.submit(unsigned)["reason"] == "bad signature"
    assert Verifier(dict(FL)).submit(sm("B1", "a1", "op1", "d1", 8))["ok"] is False  # no registry, no floors


def test_tampered_value_breaks_signature():
    x = sm("B1", "a1", "op1", "d1", 8)
    x.value = 30
    assert FV().submit(x)["reason"] == "bad signature"


def test_device_cannot_switch_operator():
    R = reg()
    with pytest.raises(ContractError):
        R.register("op9", b"k9", ["d1"])


def test_disagreement_stays_pending():
    V = FV()
    V.submit(sm("B1", "a1", "op1", "d1", 4))
    r = V.submit(sm("B1", "a2", "op2", "d2", 8))
    assert r["state"] == "pending"


def test_late_confirmer_paid_outlier_not():
    V = FV()
    V.submit(sm("B1", "a1", "op1", "d1", 8))
    V.submit(sm("B1", "a2", "op2", "d2", 8))
    assert V.submit(sm("B1", "a3", "op3", "d3", 9))["paid"] == EARN["floors_confirmed"]
    assert V.submit(sm("B1", "a4", "op4", "d4", 20))["paid"] == 0
    assert V.submit(sm("B1", "a5", "op1", "d1b", 8))["paid"] == 0  # op1 already counted (second device, same operator)


def test_floors_value_bounds():
    V = FV()
    for bad in [0, 81, "8", 8.5, None]:
        assert V.submit(sm("B1", "a1", "op1", "d1", bad))["ok"] is False


def test_spend_needs_balance_after_free_quota():
    V = Verifier({"001": {"kind": "photo", "verdict": "consistent"}})
    for _ in range(FREE_BRAIN_CALLS_PER_DAY):
        assert V.spend("a1", "brain_call", day=1)["spent"] == 0
    assert V.spend("a1", "brain_call", day=1)["ok"] is False  # quota used, no CRD
    V.submit(m("001", "a1", "op1", "d1", {"verdict": "consistent"}))
    assert V.spend("a1", "brain_call", day=1)["spent"] == 1
    assert V.ledger.balance("a1") == 0
    assert V.spend("a1", "brain_call", day=2)["spent"] == 0  # new day, new quota
    assert V.spend("a1", "teleport")["ok"] is False


def test_anchor_matches_head():
    L = Ledger()
    L._append("earn", "a", 1, "j")
    assert L.anchor() == {"seq": 0, "head": L.head, "contract": "0.2"}


# ---------------- recreate ("art") jobs
from world_contract import public_job, image_score, RECREATE_MAX_ATTEMPTS, RECREATE_DAILY_CAP  # noqa: E402

TARGET = [(i * 37 + (i // 8) * 11) % 256 for i in range(64)]   # an 8x8 test picture


def art_job(jid="A1"):
    return {jid: {"job_kind": "recreate", "id": jid, "target": TARGET, "size": [8, 8],
                  "hint": "8x8 grayscale, diagonal bands", "license": "own"}}


def test_recreate_target_never_public():
    pj = public_job(art_job()["A1"])
    assert "target" not in pj and pj["hint"]


def test_image_score_bounds():
    assert image_score(TARGET, TARGET) == 1.0
    inv = [255 - v for v in TARGET]
    assert image_score(inv, TARGET) < 0.5
    for bad in [TARGET[:10], [300] * 64, ["x"] * 64, None]:
        with pytest.raises(ContractError):
            image_score(bad, TARGET)


def test_recreate_pays_improvement_only_and_limits_attempts():
    V = Verifier(art_job())
    flat = [128] * 64
    r = V.submit(m("A1", "a1", "op1", "d1", {"image": flat}))
    assert r["paid"] == 0
    near = [min(255, v + 10) for v in TARGET]
    r = V.submit(m("A1", "a1", "op1", "d1", {"image": near}))
    assert r["score"] >= 0.9 and r["paid"] == 3
    r = V.submit(m("A1", "a1", "op1", "d1", {"image": TARGET}))
    assert r["paid"] == 0                      # already paid the top tier
    for _ in range(RECREATE_MAX_ATTEMPTS - 3):
        V.submit(m("A1", "a1", "op1", "d1", {"image": flat}))
    assert V.submit(m("A1", "a1", "op1", "d1", {"image": TARGET}))["reason"] == "no attempts left"
    assert V.ledger.balance("a1") == 3 and V.ledger.verify()


def test_recreate_daily_cap():
    jobs = {}
    for i in range(20):
        jobs.update(art_job(f"A{i}"))
    V = Verifier(jobs)
    for i in range(20):
        V.submit(m(f"A{i}", "a1", "op1", "d1", {"image": TARGET}))
    assert V.ledger.balance("a1") == RECREATE_DAILY_CAP
