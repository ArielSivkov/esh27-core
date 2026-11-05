"""Ledger-only economic simulation.

Fee and supply dynamics do not depend on consensus details, so this runs the
ledger alone, many blocks fast, using the block interval measured by the
consensus experiments. Demand reacts to price: each transaction carries a
maximum fee its sender will pay, and is not sent when the base fee is higher.
"""
import math
import random

from .ledger import TOTAL_SUPPLY, Ledger


def poisson(rng, lam):
    if lam < 30:
        L, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= rng.random()
            if p <= L:
                return k
            k += 1
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def run(cfg, block_interval, tps_fn, n_blocks, seed=27, max_willing=0.05):
    rng = random.Random(seed)
    led = Ledger(cfg, cfg.n_validators, cfg.n_users)
    nu = cfg.n_users
    rows = []
    for h in range(1, n_blocks + 1):
        demand = poisson(rng, tps_fn(h) * block_interval)
        fee = led.base_fee
        sent = 0
        transfers = []
        for _ in range(demand):
            if rng.uniform(cfg.min_fee, max_willing) < fee:
                continue  # too expensive for this sender right now
            if sent >= cfg.max_block_txs:
                break
            sent += 1
            transfers.append((rng.randrange(nu), rng.randrange(nu), 1.0))
        proposer = h % cfg.n_validators
        used = led.apply_transfers(proposer, transfers)
        led.end_block(h, proposer, used)
        rows.append((h, h * block_interval, demand, used, led.base_fee, led.burned,
                     led.rewards_total, led.charity, led.circulating()))
    assert abs(led.accounted() - TOTAL_SUPPLY) < 1e-3, "supply leak"
    return led, rows
