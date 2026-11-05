"""Builds one network, runs it, and records what happened."""
import statistics
from dataclasses import dataclass, field, replace

from .ledger import Ledger
from .node import Node
from .sim import Network, Sim, Tx


@dataclass
class Config:
    n_validators: int = 27
    n_users: int = 2000
    seed: int = 27
    duration: float = 60.0
    tps: float = 200.0
    # network
    latency_median: float = 0.040
    latency_sigma: float = 0.35
    bandwidth_bps: float = 100e6
    drop: float = 0.0
    slow_factor: float = 8.0
    gossip_fanout: int = 1
    # sizes and CPU costs
    tx_bytes: int = 250
    vote_bytes: int = 150
    exec_cost: float = 20e-6
    verify_cost: float = 60e-6  # overwritten by the measured Ed25519 verify time
    # consensus timing
    timeout_propose: float = 0.6
    timeout_vote: float = 0.3
    timeout_delta: float = 0.2
    timeout_commit: float = 0.25
    max_block_txs: int = 4000
    rebroadcast: float = 1.0  # stuck-height re-gossip interval (s)
    jail_blocks: int = 0  # 0 = plain round-robin proposer rotation
    # economics
    base_fee: float = 0.01
    min_fee: float = 0.001
    block_reward: float = 2.0
    halving_blocks: int = 10_000_000
    slash_fraction: float = 0.10
    # faults: list of (time, action, [node indices]) with action crash|restore
    behaviors: dict = field(default_factory=dict)
    schedule: list = field(default_factory=list)

    def with_(self, **kw):
        return replace(self, **kw)


class World:
    def __init__(self, cfg):
        self.cfg = cfg
        self.sim = Sim(cfg.seed)
        self.net = Network(self.sim, cfg)
        self.net.on_commit = self.on_commit
        self.nodes = [Node(i, self.net, cfg, cfg.behaviors.get(i, "honest")) for i in range(cfg.n_validators)]
        self.net.nodes = self.nodes
        self.ledger = Ledger(cfg, cfg.n_validators, cfg.n_users)
        self.canonical = {}  # height -> (hash, time, round, ntx)
        self.forks = []
        self.tx_latency = []
        self.next_tx = 0
        self.timeline = []  # per block: height, t, round, ntx, base_fee, burned, charity

    # ---------- load ----------
    def _schedule_tx(self):
        if self.cfg.tps <= 0:
            return
        self.sim.after(self.sim.rng.expovariate(self.cfg.tps), self._new_tx)

    def _new_tx(self):
        rng = self.sim.rng
        nu = self.cfg.n_users
        s = rng.randrange(nu)
        t = rng.randrange(nu)
        amount = round(rng.uniform(0.1, 50.0), 2)
        now = self.sim.t
        visible = now + self.net.latency(self.nodes[0], self.nodes[1])
        self.net.mempool.add(Tx(self.next_tx, s, t, amount, now, visible))
        self.next_tx += 1
        self._schedule_tx()

    # ---------- commits ----------
    def on_commit(self, node, block):
        h = block.height
        if h in self.canonical:
            if self.canonical[h][0] != block.hash and node.behavior == "honest":
                self.forks.append((h, node.i))
            return
        if node.behavior != "honest":
            return  # canonical history is what honest nodes commit
        t = self.sim.t
        self.canonical[h] = (block.hash, t, block.round, len(block.txs))
        committed = self.net.mempool.committed
        for tx in block.txs:
            committed.add(tx.id)
            self.tx_latency.append(t - tx.submit_t)
        self.ledger.apply_block(block)
        self.timeline.append((h, t, block.round, len(block.txs), self.ledger.base_fee,
                              self.ledger.burned, self.ledger.charity))

    # ---------- run ----------
    def run(self):
        for t, action, idxs in self.cfg.schedule:
            for i in idxs:
                self.sim.at(t, getattr(self.nodes[i], action))
        for n in self.nodes:
            if not n.crashed:
                n.start()
        self._schedule_tx()
        self.sim.run(self.cfg.duration)
        self.check_safety()
        return self.summary()

    def check_safety(self):
        honest = [n for n in self.nodes if n.behavior == "honest"]
        for a in honest:
            for b in honest:
                for x, y in zip(a.chain, b.chain):
                    if x != y:
                        self.forks.append(("prefix", a.i, b.i))
                        return

    def summary(self):
        cfg = self.cfg
        times = [v[1] for _, v in sorted(self.canonical.items())]
        intervals = [b - a for a, b in zip(times, times[1:])]
        heights = len(self.canonical)
        lat = sorted(self.tx_latency)
        txs = sum(v[3] for v in self.canonical.values())
        rounds = [v[2] for v in self.canonical.values()]

        def pct(p):
            return lat[min(len(lat) - 1, int(p * len(lat)))] if lat else None

        return {
            "validators": cfg.n_validators,
            "blocks": heights,
            "duration_s": cfg.duration,
            "offered_tps": cfg.tps,
            "achieved_tps": txs / cfg.duration,
            "block_interval_mean_s": statistics.mean(intervals) if intervals else None,
            "block_interval_max_s": max(intervals) if intervals else None,
            "finality_p50_s": pct(0.50),
            "finality_p95_s": pct(0.95),
            "finality_p99_s": pct(0.99),
            "extra_rounds": sum(1 for r in rounds if r > 0),
            "msgs_per_block": self.net.msgs / heights if heights else None,
            "mb_per_block": self.net.bytes / heights / 1e6 if heights else None,
            "backlog_txs": sum(1 for t in self.net.mempool.q if t.id not in self.net.mempool.committed),
            "forks": len(self.forks),
            "evidence_detected": len(set().union(*[n.evidence for n in self.nodes if n.behavior == "honest"]) if self.nodes else set()),
            "validators_slashed": len(self.ledger.slashed),
            "burned": self.ledger.burned,
            "charity": self.ledger.charity,
            "supply_check_ok": abs(self.ledger.accounted() - 270_000_000.0) < 1e-3,
            "sim_events": self.sim.events,
        }
