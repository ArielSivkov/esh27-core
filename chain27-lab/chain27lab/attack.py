"""Coordinated attack by a colluding group of validators (experiment 02).

The colluders act as one adversary with a global view of the network. They
split the honest validators into two halves, X and Y. Whenever a colluder is
the proposer, it sends block A to X and block B to Y, and every colluder
prevotes and precommits A towards X and B towards Y. Optionally the adversary
also controls the network and drops all traffic between X and Y.

In rounds with an honest proposer the colluders vote nil. That keeps the
rounds moving (silence would freeze everyone in round 0, so the attacker's
own proposer turn would never come) and, once they hold more than f = 8 of
the 27 validators, it stops honest blocks from reaching a quorum.
"""
from .node import Block, Proposal, Vote


class Adversary:
    def __init__(self, world, colluders, partition):
        self.w = world
        self.col = sorted(colluders)
        n = len(world.nodes)
        honest = [i for i in range(n) if i not in self.col]
        half = len(honest) // 2
        self.X = honest[:half]
        self.Y = honest[half:]
        if partition:
            world.net.side = {**{i: "X" for i in self.X}, **{i: "Y" for i in self.Y}}
        self.attacked = set()
        self.nilled = set()
        self.attacks = 0

    def start(self):
        self.w.sim.after(0.05, self.tick)

    def tick(self):
        nodes = self.w.nodes
        hx, hy = nodes[self.X[0]], nodes[self.Y[0]]
        if hx.h == hy.h and hx.last_hash == hy.last_hash:
            h = hx.h
            for r in sorted({nodes[i].r for i in self.X + self.Y if nodes[i].h == h}):
                p = hx.proposer(h, r)
                if p in self.col and (h, r) not in self.attacked:
                    self.attack(h, r, p, hx.last_hash)
                elif p not in self.col and (h, r) not in self.nilled:
                    self.vote_nil(h, r)
        self.w.sim.after(0.05, self.tick)

    def vote_nil(self, h, r):
        self.nilled.add((h, r))
        w, net, cfg = self.w, self.w.net, self.w.cfg
        nodes = w.nodes
        for c in self.col:
            for kind in ("pv", "pc"):
                for d in self.X + self.Y:
                    net.send(nodes[c], nodes[d], Vote(kind, h, r, None, c),
                             size=cfg.vote_bytes, extra=cfg.verify_cost)

    def attack(self, h, r, p, parent):
        self.attacked.add((h, r))
        self.attacks += 1
        w, net, cfg = self.w, self.w.net, self.w.cfg
        txs = tuple(net.mempool.take(w.sim.t, cfg.max_block_txs))
        a = Block(h, r, p, parent, txs, (), variant=11)
        b = Block(h, r, p, parent, txs[: len(txs) // 2], (), variant=12)
        nodes = w.nodes
        src = nodes[p]
        for side, blk in ((self.X, a), (self.Y, b)):
            size = 300 + cfg.tx_bytes * len(blk.txs)
            for d in side:
                net.send(src, nodes[d], Proposal(h, r, blk, -1, p), size=size)
            for c in self.col:
                for kind in ("pv", "pc"):
                    for d in side:
                        net.send(nodes[c], nodes[d], Vote(kind, h, r, blk.hash, c),
                                 size=cfg.vote_bytes, extra=cfg.verify_cost)
