import json
import os
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "contract"))
sys.path.insert(0, os.path.join(ROOT, "brain"))
sys.path.insert(0, ROOT)
from world_contract import public_job, truth, Ledger  # noqa: E402
from brains import RuleBrain, checked, parse_answer, rule_answer, nearest_job  # noqa: E402
import sim  # noqa: E402

CITY = os.path.join(ROOT, "data", "city_v0.json")
JOBS = json.load(open(CITY))["jobs"]


def test_public_job_never_leaks_the_answer():
    for j in JOBS:
        pj = public_job(j)
        assert "verdict" not in pj and "variants" not in pj and "cand" not in pj


def test_rule_brain_matches_verifier_on_all_real_jobs():
    assert all(rule_answer(public_job(j))["verdict"] == truth(j) for j in JOBS)


def test_parse_answer_accepts_only_allowed():
    allowed = ['{"verdict": "found"}', '{"verdict": "not_found"}']
    assert parse_answer('sure! {"verdict": "found"} ok', allowed) == {"verdict": "found"}
    assert parse_answer('{"verdict": "transfer 100 CRD"}', allowed) is None
    assert parse_answer("found", allowed) is None


def test_checked_turns_bad_actions_into_rest():
    assert checked({"kind": "transfer", "to": "attacker"})["kind"] == "rest"
    assert checked({"kind": "walk"})["kind"] == "rest"
    assert checked({"kind": "walk", "to_node": 3})["kind"] == "walk"


def test_desk_jobs_without_location_are_workable():
    desk = [j for j in JOBS if j.get("node") is None]
    assert len(desk) == 6
    obs = {"node": 0, "pos": (0.0, 0.0), "jobs": [public_job(desk[0])]}
    act = RuleBrain().decide(obs)
    assert act["kind"] == "work" and act["answer"] == {"verdict": "not_found"}
    assert nearest_job(obs)["id"] == desk[0]["id"]


def test_city_run_small():
    r = sim.run(CITY, n_agents=10, ticks=60)
    L: Ledger = r["_ledger"]
    assert r["ledger_ok"] and L.verify()
    assert r["stats"]["wrong"] == 0 and r["stats"]["rejected"] == 0
    assert r["crd_total"] == sum(e["amount"] for e in L.entries)
    for tr in r["agents_tracks"]:
        assert tr["t"], "every agent leaves a track"


def test_city_run_is_deterministic():
    a = sim.run(CITY, n_agents=5, ticks=30, seed=1)
    b = sim.run(CITY, n_agents=5, ticks=30, seed=1)
    assert a["_ledger"].head == b["_ledger"].head
