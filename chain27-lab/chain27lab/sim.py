"""Discrete-event simulator, network model and global mempool.

Everything runs in simulated time (seconds), driven by one seeded RNG, so a
scenario with the same seed always produces the same numbers.
"""
import heapq
import math
import random
from collections import deque


class Sim:
    def __init__(self, seed=27):
        self.t = 0.0
        self.q = []
        self.seq = 0
        self.rng = random.Random(seed)
        self.events = 0

    def at(self, t, fn, *args):
        heapq.heappush(self.q, (t, self.seq, fn, args))
        self.seq += 1

    def after(self, dt, fn, *args):
        self.at(self.t + dt, fn, *args)

    def run(self, until):
        q = self.q
        while q and q[0][0] <= until:
            t, _, fn, args = heapq.heappop(q)
            self.t = t
            self.events += 1
            fn(*args)
        self.t = until


class Tx:
    __slots__ = ("id", "sender", "to", "amount", "submit_t", "visible_t")

    def __init__(self, id, sender, to, amount, submit_t, visible_t):
        self.id = id
        self.sender = sender
        self.to = to
        self.amount = amount
        self.submit_t = submit_t
        self.visible_t = visible_t


class Mempool:
    """Shared mempool. A transaction becomes visible to proposers after one
    gossip delay; this abstracts per-node mempools, which would multiply the
    event count by the number of nodes without changing consensus behaviour."""

    def __init__(self):
        self.q = deque()
        self.committed = set()

    def add(self, tx):
        self.q.append(tx)

    def take(self, now, max_n):
        q = self.q
        committed = self.committed
        while q and q[0].id in committed:
            q.popleft()
        out = []
        scanned = 0
        for tx in q:
            scanned += 1
            if scanned > max_n * 3 or len(out) >= max_n:
                break
            if tx.visible_t <= now and tx.id not in committed:
                out.append(tx)
        return out

    def __len__(self):
        return len(self.q)


class Network:
    """Full mesh: every node has a direct link to every other node."""

    def __init__(self, sim, cfg):
        self.sim = sim
        self.cfg = cfg
        self.nodes = []
        self.msgs = 0
        self.bytes = 0
        self.mempool = Mempool()
        self.included_evidence = set()
        self._mu = math.log(cfg.latency_median)

    def latency(self, a, b):
        cfg = self.cfg
        base = math.exp(self._mu + cfg.latency_sigma * self.sim.rng.gauss(0, 1))
        return base * max(a.slow, b.slow)

    def send(self, src, dst, msg, size=150, extra=0.0):
        if src.crashed or dst.crashed:
            return
        if self.cfg.drop and self.sim.rng.random() < self.cfg.drop:
            return
        self.msgs += 1
        self.bytes += size
        tx_time = size * 8 / self.cfg.bandwidth_bps
        self.sim.after(self.latency(src, dst) + tx_time + extra, dst.receive, msg)
