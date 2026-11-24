"""The agent city, running under the contract.

  python sim.py [--agents 100] [--ticks 360] [--brain rule|tiny] [--out out/]

Each agent lives on a real Ashdod building (city_v0.json, from the twin world's tiles), walks the
real street graph at 1.4 m/s (1 tick = 10 s), takes the nearest job it has not done, and hands in
work through the contract. Only the Verifier pays CRD. Output:
  out/run.json     - summary + agent tracks (every 6th tick) for the world adapter
  out/ledger.jsonl - the hash-chained ledger
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "contract"))
sys.path.insert(0, os.path.join(HERE, "brain"))
from world_contract import Measurement, Verifier, public_job, CONTRACT_VERSION  # noqa: E402
from brains import RuleBrain, checked, at_job, nearest_job  # noqa: E402

TICK_S = 10
SPEED = 1.4


def load_city(path: str) -> dict:
    d = json.load(open(path))
    nodes = d["n"]
    adj: dict[int, list[tuple[int, float]]] = {}
    for e in d["e"]:
        u, v = e[0], e[1]
        w = e[2] if len(e) > 2 else math.dist(nodes[u], nodes[v])
        adj.setdefault(u, []).append((v, w))
        adj.setdefault(v, []).append((u, w))
    return {"o": d["o"], "nodes": nodes, "adj": adj, "buildings": d["b"], "jobs": d["jobs"]}


def shortest_path(adj, nodes, s: int, t: int) -> list[int]:
    if s == t:
        return [s]
    dist, prev, pq = {s: 0.0}, {}, [(0.0, s)]
    while pq:
        du, u = heapq.heappop(pq)
        if u == t:
            break
        if du > dist.get(u, math.inf):
            continue
        for v, w in adj.get(u, ()):
            nd = du + w
            if nd < dist.get(v, math.inf):
                dist[v], prev[v] = nd, u
                heapq.heappush(pq, (nd, v))
    if t not in prev:
        return []
    path = [t]
    while path[-1] != s:
        path.append(prev[path[-1]])
    return path[::-1]


def nearest_node(nodes, x, y, cand=None) -> int:
    rng = cand if cand is not None else range(len(nodes))
    return min(rng, key=lambda i: (nodes[i][0] - x) ** 2 + (nodes[i][1] - y) ** 2)


class Agent:
    def __init__(self, aid: str, operator: str, device: str, plot: int, node: int, pos):
        self.id, self.operator, self.device, self.plot = aid, operator, device, plot
        self.node, self.pos = node, list(pos)
        self.path: list[int] = []
        self.done: set[str] = set()
        self.target_job: str | None = None
        self.track: list[list[float]] = []


def run(city_path: str, n_agents: int = 100, ticks: int = 360, brain=None, seed: int = 27,
        operator: str = "city-lab") -> dict:
    rnd = random.Random(seed)
    C = load_city(city_path)
    nodes, adj = C["nodes"], C["adj"]
    connected = [i for i in range(len(nodes)) if i in adj]
    jobs = {j["id"]: j for j in C["jobs"]}
    V = Verifier(jobs)
    brain = brain or RuleBrain()
    plots = rnd.sample(range(len(C["buildings"])), n_agents)
    agents = []
    for k, bi in enumerate(plots):
        b = C["buildings"][bi]
        nn = nearest_node(nodes, b[0], b[1], connected)
        # all city agents share ONE operator: they can never confirm each other's floor counts (sybil rule)
        agents.append(Agent(f"a{k:03d}", operator, f"{operator}-sim", bi, nn, nodes[nn]))
    stats = {"walk": 0, "work": 0, "rest": 0, "paid": 0, "wrong": 0, "rejected": 0, "brain_spend_failed": 0}
    step = SPEED * TICK_S
    for t in range(ticks):
        for a in agents:
            if a.path:  # keep walking
                budget = step
                while a.path and budget > 0:
                    nxt = nodes[a.path[0]]
                    d = math.dist(a.pos, nxt)
                    if d <= budget:
                        budget -= d
                        a.pos = list(nxt)
                        a.node = a.path.pop(0)
                    else:
                        f = budget / d
                        a.pos = [a.pos[0] + (nxt[0] - a.pos[0]) * f, a.pos[1] + (nxt[1] - a.pos[1]) * f]
                        budget = 0
                if t % 6 == 0:
                    a.track.append([t, round(a.pos[0], 1), round(a.pos[1], 1)])
                continue
            obs = {"agent_id": a.id, "operator_id": a.operator, "tick": t, "node": a.node,
                   "pos": tuple(a.pos), "plot": str(a.plot), "credits": V.ledger.balance(a.id),
                   "jobs": [public_job(j) for jid, j in jobs.items() if jid not in a.done]}
            if getattr(brain, "costs_crd", False):
                nj = nearest_job(obs)
                if nj is not None and at_job(obs, nj) and not V.spend(a.id, "brain_call", f"t{t}")["ok"]:
                    stats["brain_spend_failed"] += 1  # cannot afford a model call: fall back to the rule brain
                    act = checked(RuleBrain().decide(obs))
                else:
                    act = checked(brain.decide(obs))
            else:
                act = checked(brain.decide(obs))
            stats[act["kind"]] += 1
            if act["kind"] == "walk":
                p = shortest_path(adj, nodes, a.node, act["to_node"])
                if len(p) > 1:
                    a.path = p[1:]
                else:  # unreachable job: skip it
                    jid = next((j["id"] for j in obs["jobs"] if j["node"] == act["to_node"]), None)
                    if jid:
                        a.done.add(jid)
            elif act["kind"] == "work":
                r = V.submit(Measurement(act["job_id"], "", a.id, a.operator, a.device, act["answer"]))
                a.done.add(act["job_id"])
                if not r.get("ok"):
                    stats["rejected"] += 1
                elif r.get("paid"):
                    stats["paid"] += 1
                else:
                    stats["wrong"] += 1
            if t % 6 == 0:
                a.track.append([t, round(a.pos[0], 1), round(a.pos[1], 1)])
    balances = sorted((V.ledger.balance(a.id) for a in agents), reverse=True)
    return {
        "contract": CONTRACT_VERSION, "brain": brain.name, "agents": n_agents, "ticks": ticks,
        "tick_s": TICK_S, "frame": "city_v0 local metres, origin o", "o": C["o"],
        "stats": stats, "ledger_ok": V.ledger.verify(), "ledger_entries": len(V.ledger.entries),
        "crd_total": sum(balances), "crd_top5": balances[:5], "crd_median": balances[len(balances) // 2],
        "jobs_done_by_anyone": len({e["ref"] for e in V.ledger.entries if e["kind"] == "earn"}),
        "agents_tracks": [{"id": a.id, "plot": a.plot, "t": a.track} for a in agents],
        "_ledger": V.ledger,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", type=int, default=100)
    ap.add_argument("--ticks", type=int, default=360)
    ap.add_argument("--brain", default="rule")
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--city", default=os.path.join(HERE, "data", "city_v0.json"))
    a = ap.parse_args()
    brain = None
    if a.brain == "tiny":
        from brains import TinyLMBrain
        brain = TinyLMBrain()
    elif a.brain.startswith("hybrid:"):
        from brains import HybridBrain
        brain = HybridBrain(a.brain.split(":", 1)[1])
    res = run(a.city, a.agents, a.ticks, brain)
    os.makedirs(a.out, exist_ok=True)
    L = res.pop("_ledger")
    open(os.path.join(a.out, "ledger.jsonl"), "w").write(L.dump() + "\n")
    json.dump(res, open(os.path.join(a.out, "run.json"), "w"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({k: v for k, v in res.items() if k != "agents_tracks"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
