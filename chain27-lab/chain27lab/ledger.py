"""The test coin (ESH27-test) and its economics.

Fixed supply of 270,000,000 at genesis, nothing is ever minted afterwards.
Illustrative genesis allocation (not a decision, see the whitepaper v1.1):
  treasury   40%  pays block rewards over time
  users      20%  spread over simulated users (faucet)
  stakes     27 x 1,000,000 bonded by the validators
  reserve    the rest, locked (team / ecosystem), untouched in the lab

Per transaction fee: 50% burned, 40% to the block proposer, 10% to the
charity fund. Base fee follows an EIP-1559-style rule: it rises when blocks
are more than half full and falls when they are less.
"""
TOTAL_SUPPLY = 270_000_000.0


class Ledger:
    def __init__(self, cfg, n_validators, n_users):
        self.cfg = cfg
        self.n_users = n_users
        self.treasury = TOTAL_SUPPLY * 0.40
        user_pool = TOTAL_SUPPLY * 0.20
        self.users = [user_pool / n_users] * n_users
        self.stakes = [1_000_000.0] * n_validators
        self.validator_income = [0.0] * n_validators
        self.charity = 0.0
        self.burned = 0.0
        self.reserve = TOTAL_SUPPLY - self.treasury - user_pool - sum(self.stakes)
        self.base_fee = cfg.base_fee
        self.slashed = set()
        self.applied = 0
        self.rejected = 0
        self.fees_total = 0.0
        self.rewards_total = 0.0

    def accounted(self):
        return (sum(self.users) + self.treasury + sum(self.stakes) + sum(self.validator_income)
                + self.charity + self.burned + self.reserve)

    def circulating(self):
        """Everything not burned and not locked in the reserve or treasury."""
        return TOTAL_SUPPLY - self.burned - self.reserve - self.treasury

    def block_reward(self, height):
        cfg = self.cfg
        return cfg.block_reward * (0.5 ** (height // cfg.halving_blocks))

    def apply_transfers(self, proposer, transfers):
        """transfers: iterable of (sender, to, amount)."""
        fee = self.base_fee
        users = self.users
        used = 0
        for s, t, amount in transfers:
            if users[s] >= amount + fee:
                users[s] -= amount + fee
                users[t] += amount
                used += 1
            else:
                self.rejected += 1
        total_fee = used * fee
        self.burned += total_fee * 0.5
        self.validator_income[proposer] += total_fee * 0.4
        self.charity += total_fee * 0.1
        self.fees_total += total_fee
        self.applied += used
        return used

    def end_block(self, height, proposer, used, evidence=()):
        reward = min(self.treasury, self.block_reward(height))
        self.treasury -= reward
        to_charity = reward * self.cfg.charity_reward_share
        self.charity += to_charity
        self.validator_income[proposer] += reward - to_charity
        self.rewards_total += reward
        for (validator, _h, _r) in evidence:
            if validator not in self.slashed:
                penalty = self.stakes[validator] * self.cfg.slash_fraction
                self.stakes[validator] -= penalty
                self.burned += penalty
                self.slashed.add(validator)
        cfg = self.cfg
        target = cfg.max_block_txs / 2
        self.base_fee *= 1 + 0.125 * (used - target) / target
        self.base_fee = max(self.base_fee, cfg.min_fee)

    def apply_block(self, block):
        used = self.apply_transfers(block.proposer, ((t.sender, t.to, t.amount) for t in block.txs))
        self.end_block(block.height, block.proposer, used, block.evidence)
        return used
