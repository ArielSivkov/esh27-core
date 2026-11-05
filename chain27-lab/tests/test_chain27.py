"""Core guarantees of the lab chain. Run: python -m pytest tests/ (or python tests/test_chain27.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from chain27lab.ledger import TOTAL_SUPPLY  # noqa: E402
from chain27lab.world import Config, World  # noqa: E402

BASE = Config(duration=15.0, jail_blocks=100)


def run(**kw):
    w = World(BASE.with_(**kw))
    return w, w.run()


def test_baseline_commits_and_conserves_supply():
    w, s = run()
    assert s["blocks"] > 20
    assert s["forks"] == 0
    assert abs(w.ledger.accounted() - TOTAL_SUPPLY) < 1e-3


def test_survives_eight_crashed():
    # 8 consecutive proposers are down, so the first block needs 8 rounds
    # (~16 s) before jailing kicks in; give it time.
    _, s = run(duration=40.0, behaviors={i: "crash" for i in range(8)})
    assert s["blocks"] > 20 and s["forks"] == 0


def test_halts_with_nine_crashed():
    _, s = run(behaviors={i: "crash" for i in range(9)})
    assert s["blocks"] == 0


def test_eight_equivocators_no_fork_and_slashed():
    w, s = run(duration=30.0, behaviors={i: "equivocate" for i in range(8)})
    assert s["forks"] == 0
    assert s["blocks"] > 5
    assert s["validators_slashed"] >= 1
    assert abs(w.ledger.accounted() - TOTAL_SUPPLY) < 1e-3


def test_recovers_after_restore():
    sched = [(3.0, "crash", list(range(9))), (8.0, "restore", [0])]
    w, s = run(duration=20.0, schedule=sched)
    times = [v[1] for v in w.canonical.values()]
    assert any(3.5 < t < 8.0 for t in times) is False  # halted while 9 were down
    assert any(t > 8.0 for t in times)  # and resumed after one came back
    assert s["forks"] == 0


def test_deterministic():
    _, a = run(seed=5)
    _, b = run(seed=5)
    assert a == b


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
