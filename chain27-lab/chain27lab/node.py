"""Validator node running a simplified Tendermint-style BFT consensus.

Per height: rounds of PROPOSE -> PREVOTE -> PRECOMMIT. A block commits when a
node holds the proposal and 2f+1 precommits for it. Locking (locked value and
round) and the valid-round rule keep honest nodes from committing different
blocks at the same height while at most f validators are Byzantine.

Votes are authenticated by the simulator (the sender field is trusted). The CPU
cost of real Ed25519 verification is added to message delays instead; see
crypto_bench.py.
"""
import hashlib
from collections import defaultdict

GENESIS = "0" * 64


class Block:
    __slots__ = ("height", "round", "proposer", "parent", "txs", "evidence", "hash")

    def __init__(self, height, round, proposer, parent, txs, evidence, variant=0):
        self.height = height
        self.round = round
        self.proposer = proposer
        self.parent = parent
        self.txs = txs
        self.evidence = evidence
        h = hashlib.sha256()
        h.update(f"{height}|{round}|{proposer}|{parent}|{variant}|{evidence}|".encode())
        h.update(",".join(str(t.id) for t in txs).encode())
        self.hash = h.hexdigest()


class Proposal:
    __slots__ = ("height", "round", "block", "valid_round", "sender")

    def __init__(self, height, round, block, valid_round, sender):
        self.height = height
        self.round = round
        self.block = block
        self.valid_round = valid_round
        self.sender = sender


class Vote:
    __slots__ = ("kind", "height", "round", "value", "sender")

    def __init__(self, kind, height, round, value, sender):
        self.kind = kind  # "pv" prevote, "pc" precommit
        self.height = height
        self.round = round
        self.value = value  # block hash or None (nil)
        self.sender = sender


class Node:
    def __init__(self, idx, net, cfg, behavior="honest"):
        self.i = idx
        self.net = net
        self.sim = net.sim
        self.cfg = cfg
        self.behavior = behavior
        self.crashed = behavior == "crash"
        self.slow = cfg.slow_factor if behavior == "slow" else 1.0
        self.chain = []
        self.last_hash = GENESIS
        self.h = 1
        self.r = 0
        self.step = None
        self.decided = False
        self.locked = None
        self.locked_round = -1
        self.valid = None
        self.valid_round = -1
        self.proposals = {}
        self.blocks = {}
        self.votes = defaultdict(dict)
        self.seen = set()
        self.round_senders = defaultdict(set)
        self.flags = set()
        self.evidence = set()
        self.jailed = {}  # validator -> height until which it may not propose

    # ---------- helpers ----------
    @property
    def n(self):
        return len(self.net.nodes)

    @property
    def f(self):
        return (self.n - 1) // 3

    @property
    def quorum(self):
        return (2 * self.n) // 3 + 1

    @property
    def byzantine(self):
        return self.behavior == "equivocate"

    def proposer(self, h, r):
        """Round-robin. With jailing on, validators that recently failed to
        propose (or were caught equivocating) are skipped. The jail list is
        derived only from committed blocks, so all honest nodes agree on it."""
        n = self.n
        if not self.cfg.jail_blocks:
            return (h + r) % n
        cands = [v for v in range(n) if self.jailed.get(v, 0) < h] or list(range(n))
        return cands[(h + r) % len(cands)]

    def count(self, h, r, kind, value):
        return sum(1 for v in self.votes[(h, r, kind)].values() if v == value)

    def valid_block(self, b):
        return b.height == self.h and b.parent == self.last_hash

    def peers(self):
        return [p for p in self.net.nodes if p is not self]

    # ---------- lifecycle ----------
    def start(self):
        if self.behavior == "collude":
            return  # driven by the coordinated Adversary (attack.py)
        self.enter_height(1)

    def crash(self):
        self.crashed = True

    def restore(self):
        live = [p for p in self.net.nodes if not p.crashed and p.behavior == "honest"]
        self.crashed = False
        if live:
            src = max(live, key=lambda p: len(p.chain))
            self.chain = list(src.chain)
            self.last_hash = src.last_hash
            self.jailed = dict(src.jailed)
        self.enter_height(len(self.chain) + 1)

    def enter_height(self, h):
        if self.crashed:
            return
        self.h = h
        self.decided = False
        self.locked, self.locked_round = None, -1
        self.valid, self.valid_round = None, -1
        self.flags = set()
        self.sim.after(self.cfg.rebroadcast, self._heartbeat, h)
        if h % 20 == 0:
            self._gc(h)
        self.start_round(0)
        rounds = sorted({k[1] for k in self.round_senders if k[0] == h})
        for r in rounds:
            if self.h != h or self.decided:
                break
            self.check(h, r)

    def _heartbeat(self, h):
        """Re-send this node's own messages for the current round while the
        height is stuck. Models the continuous state gossip of real BFT
        engines; without it, votes sent to a node while it was down are lost
        and a network at exactly 2f+1 live nodes can stall forever."""
        if self.crashed or self.h != h or self.decided:
            return
        r = self.r
        prop = self.proposals.get((h, r))
        if prop is not None and prop[0].proposer == self.i:
            b = prop[0]
            size = 300 + self.cfg.tx_bytes * len(b.txs)
            for p in self.peers():
                self.net.send(self, p, Proposal(h, r, b, prop[1], self.i), size=size)
        for kind in ("pv", "pc"):
            mine = self.votes[(h, r, kind)].get(self.i, "absent")
            if mine != "absent":
                for p in self.peers():
                    self.net.send(self, p, Vote(kind, h, r, mine, self.i), size=self.cfg.vote_bytes,
                                  extra=self.cfg.verify_cost)
        self.sim.after(self.cfg.rebroadcast, self._heartbeat, h)

    def _gc(self, h):
        old = h - 3
        for d in (self.votes, self.round_senders):
            for k in [k for k in d if k[0] < old]:
                del d[k]
        for k in [k for k in self.proposals if k[0] < old]:
            del self.proposals[k]
        self.blocks = {k: b for k, b in self.blocks.items() if b.height >= old}
        self.seen = {s for s in self.seen if s[1] >= old}

    def start_round(self, r):
        h = self.h
        self.r = r
        self.step = "propose"
        cfg = self.cfg
        if self.proposer(h, r) == self.i:
            block = self.valid if self.valid is not None else self.make_block(r)
            self.broadcast_proposal(block, self.valid_round)
        else:
            self.sim.after(cfg.timeout_propose + r * cfg.timeout_delta, self.on_timeout_propose, h, r)
        self.check(h, r)

    def make_block(self, r, variant=0, txs=None):
        if txs is None:
            txs = tuple(self.net.mempool.take(self.sim.t, self.cfg.max_block_txs))
        evid = tuple(sorted(self.evidence - self.net.included_evidence))[:10]
        return Block(self.h, r, self.i, self.last_hash, txs, evid, variant)

    # ---------- sending ----------
    def broadcast_proposal(self, block, valid_round):
        cfg = self.cfg
        h, r = self.h, self.r
        size = 300 + cfg.tx_bytes * len(block.txs)
        per_peer = size * 8 / cfg.bandwidth_bps  # proposer uplink is shared
        exec_cost = cfg.exec_cost * len(block.txs)
        peers = self.peers()
        blocks = [block] * len(peers)
        if self.byzantine and valid_round == -1:
            # equivocation: half the peers get one block, half get another
            alt = self.make_block(r, variant=1, txs=block.txs[: len(block.txs) // 2])
            half = len(peers) // 2
            blocks = [block] * half + [alt] * (len(peers) - half)
            self.blocks[alt.hash] = alt
        self.receive(Proposal(h, r, block, valid_round, self.i))
        for k, (p, b) in enumerate(zip(peers, blocks)):
            msg = Proposal(h, r, b, valid_round, self.i)
            self.net.send(self, p, msg, size=size, extra=k * per_peer + exec_cost)

    def broadcast_vote(self, kind, value):
        h, r = self.h, self.r
        cfg = self.cfg
        peers = self.peers()
        if self.byzantine:
            others = [k for k in self.proposal_hashes(h, r) if k != value]
            alt = others[0] if others else None
            half = len(peers) // 2
            targets = [(p, value) for p in peers[:half]] + [(p, alt) for p in peers[half:]]
        else:
            targets = [(p, value) for p in peers]
        self.receive(Vote(kind, h, r, value, self.i))
        for p, v in targets:
            self.net.send(self, p, Vote(kind, h, r, v, self.i), size=cfg.vote_bytes,
                          extra=cfg.verify_cost)

    def proposal_hashes(self, h, r):
        return [b.hash for b in self.blocks.values() if b.height == h and b.round == r]

    def prevote(self, value):
        self.step = "prevote"
        self.broadcast_vote("pv", value)

    def precommit(self, value):
        self.step = "precommit"
        self.broadcast_vote("pc", value)

    # ---------- receiving ----------
    def receive(self, msg):
        if self.crashed or self.behavior == "collude":
            return
        if isinstance(msg, Vote):
            self.on_vote(msg)
        else:
            self.on_proposal(msg)

    def on_proposal(self, m):
        if m.sender != self.proposer(m.height, m.round):
            return
        key = (m.height, m.round)
        self.blocks.setdefault(m.block.hash, m.block)
        if key not in self.proposals:
            self.proposals[key] = (m.block, m.valid_round)
        self.round_senders[key].add(m.sender)
        if m.height == self.h:
            self.check(m.height, m.round)

    def on_vote(self, v):
        sig = (v.sender, v.height, v.round, v.kind, v.value)
        if sig in self.seen:
            return
        self.seen.add(sig)
        box = self.votes[(v.height, v.round, v.kind)]
        prev = box.get(v.sender, "absent")
        if prev != "absent" and prev != v.value:
            self.evidence.add((v.sender, v.height, v.round))
            return
        box[v.sender] = v.value
        self.round_senders[(v.height, v.round)].add(v.sender)
        # gossip: honest nodes forward votes they have not seen before
        if self.behavior == "honest" and v.sender != self.i and self.cfg.gossip_fanout:
            peers = self.peers()
            for p in self.sim.rng.sample(peers, min(self.cfg.gossip_fanout, len(peers))):
                if p.i != v.sender:
                    self.net.send(self, p, v, size=self.cfg.vote_bytes, extra=self.cfg.verify_cost)
        if v.height == self.h:
            self.check(v.height, v.round)

    # ---------- the consensus rules ----------
    def check(self, h, rr):
        if self.crashed or h != self.h or self.decided:
            return
        Q = self.quorum
        # commit rule: proposal + 2f+1 precommits for it, in any round
        pcs = self.votes[(h, rr, "pc")]
        if len(pcs) >= Q:
            tally = {}
            for v in pcs.values():
                if v is not None:
                    tally[v] = tally.get(v, 0) + 1
            for value, c in tally.items():
                if c < Q:
                    continue
                if value in self.blocks and self.blocks[value].height == h:
                    self.commit(self.blocks[value])
                    return
                self.request_block(value)
        # round skip: f+1 validators already in a later round
        if rr > self.r and len(self.round_senders[(h, rr)]) >= self.f + 1:
            self.start_round(rr)
            return
        if rr != self.r:
            return
        r = self.r
        prop = self.proposals.get((h, r))
        if prop is not None and self.step == "propose":
            b, vr = prop
            if vr == -1:
                ok = self.valid_block(b) and (self.locked_round == -1 or self.locked == b.hash)
                self.prevote(b.hash if ok else None)
            elif 0 <= vr < r and self.count(h, vr, "pv", b.hash) >= Q:
                ok = self.valid_block(b) and (self.locked_round <= vr or self.locked == b.hash)
                self.prevote(b.hash if ok else None)
        if self.r != r or self.decided or self.h != h:
            return
        pv = self.votes[(h, r, "pv")]
        if self.step == "prevote" and len(pv) >= Q and ("tpv", r) not in self.flags:
            self.flags.add(("tpv", r))
            self.sim.after(self.cfg.timeout_vote + r * self.cfg.timeout_delta, self.on_timeout_prevote, h, r)
        if prop is not None and self.step in ("prevote", "precommit") and ("polka", r) not in self.flags:
            b = prop[0]
            if self.valid_block(b) and self.count(h, r, "pv", b.hash) >= Q:
                self.flags.add(("polka", r))
                self.valid, self.valid_round = b, r
                if self.step == "prevote":
                    self.locked, self.locked_round = b.hash, r
                    self.precommit(b.hash)
        if self.step == "prevote" and self.count(h, r, "pv", None) >= Q:
            self.precommit(None)
        pc = self.votes[(h, r, "pc")]
        if len(pc) >= Q and ("tpc", r) not in self.flags:
            self.flags.add(("tpc", r))
            self.sim.after(self.cfg.timeout_vote + r * self.cfg.timeout_delta, self.on_timeout_precommit, h, r)

    def request_block(self, value):
        """Block sync: a quorum committed a block this node never received
        (e.g. it got the other half of an equivocating proposal). Fetch it."""
        key = ("fetch", value)
        if key in self.flags:
            return
        self.flags.add(key)
        for p in self.peers():
            b = p.blocks.get(value)
            if b is not None and not p.crashed:
                m = Proposal(b.height, b.round, b, -1, b.proposer)
                size = 300 + self.cfg.tx_bytes * len(b.txs)
                self.net.send(p, self, m, size=size, extra=self.cfg.exec_cost * len(b.txs))
                return

    # ---------- timeouts ----------
    def on_timeout_propose(self, h, r):
        if not self.crashed and h == self.h and r == self.r and self.step == "propose" and not self.decided:
            self.prevote(None)

    def on_timeout_prevote(self, h, r):
        if not self.crashed and h == self.h and r == self.r and self.step == "prevote" and not self.decided:
            self.precommit(None)

    def on_timeout_precommit(self, h, r):
        if not self.crashed and h == self.h and r == self.r and not self.decided:
            self.start_round(r + 1)

    # ---------- commit ----------
    def commit(self, block):
        self.decided = True
        if self.cfg.jail_blocks:
            failed = [self.proposer(block.height, rr) for rr in range(block.round)]
            for v in failed:
                self.jailed[v] = block.height + self.cfg.jail_blocks
            for (v, _h, _r) in block.evidence:
                self.jailed[v] = 10 ** 12
        self.chain.append(block.hash)
        self.last_hash = block.hash
        for e in block.evidence:
            self.net.included_evidence.add(e)
        self.net.on_commit(self, block)
        self.sim.after(self.cfg.timeout_commit, self.enter_height, block.height + 1)
