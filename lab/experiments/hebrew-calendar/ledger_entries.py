"""Append the Hebrew-calendar results to lab/data/ledger.jsonl (run once, from lab/).

Usage:  cd lab && python -m experiments.hebrew-calendar.ledger_entries   (or python experiments/hebrew-calendar/ledger_entries.py)
Honest claim levels: L3 only for kernel-checked theorems in a package whose
`lake build` passed (certificate verified=true); the #guard cross-check is L1.
`review` is left empty for the makshan (foundation ד).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LAB))
from orchestrator.ledger import Attempt, ClaimLevel, append  # noqa: E402

LEDGER = LAB / "data/ledger.jsonl"
PKG = "lab/lean/Hebrew"
THM = "lab/lean/Hebrew/Hebrew/Theorems.lean"
DR = "lab/lean/Hebrew/Hebrew/DR.lean"
AGENT = "lean-agent"
MODEL = "claude (ESH27 lean-agent session 013gymVSs4M2emK7oDmKArxP)"

RAMBAM = "Rambam, Mishneh Torah, Hilchot Kiddush HaChodesh 6-8 (Sefaria, Torat Emet 363; Touger tr.) — see lab/experiments/hebrew-calendar/SOURCES.md"
RUSSINOFF = "D. M. Russinoff, Properties of the Hebrew Calendar, EPTCS 359 (2022) 48-60, doi:10.4204/EPTCS.359.6, arXiv:2205.13345"
ORACLE = "lab/experiments/novelty/sanity/hebrew_period.py (Dershowitz-Reingold style oracle)"
NOVELTY = "lab/experiments/novelty/REPORT.md (candidates 6, 7)"


def sha(p: str) -> str:
    return hashlib.sha256((LAB.parent / p).read_bytes()).hexdigest()


def cert(path: str) -> dict:
    return {"kind": "lean", "path": path, "checker": "lake build", "checker_version": "Lean 4.24.0 (leanprover/lean4:v4.24.0), core only, no Mathlib",
            "sha256": sha(path), "verified": True}


def entry(goal: str, summary: str, level: int, artifacts: list[str], sources: list[str], certificate: dict | None, outcome: str = "success") -> Attempt:
    return Attempt(goal_id=goal, agent=AGENT, method="lean-proof", claim_level=level, summary=summary,
                   outcome=outcome, artifacts=artifacts, certificate=certificate, model=MODEL,
                   sources=sources, review=None)


ENTRIES = [
    entry("HEB-0-defs", "Definitions of the fixed Hebrew calendar after Rambam Kiddush HaChodesh 6-8 in core Lean 4 (Nat only): parts, lunation 29d12h793p, BaHaRaD, 19-year cycle with leap years 3,6,8,11,14,17,19, molad Tishrei, the four dechiyot, roshHashanah, yearLength, keviyah. Cross-check: `#guard` in CrossCheck.lean agrees with hebrew_period.py for years 1..10001 (computational evidence, interpreter, not kernel).",
          ClaimLevel.L1_NUMERIC, ["lab/lean/Hebrew/Hebrew/Basic.lean", "lab/lean/Hebrew/Hebrew/CrossCheck.lean", "lab/lean/Hebrew/Hebrew/Oracle.lean", "lab/experiments/hebrew-calendar/gen_oracle.py"],
          [RAMBAM, ORACLE, NOVELTY], None),
    entry("HEB-a-lo-adu", "Theorem Hebrew.lo_adu: for every year y, Rosh Hashana is not on Sunday, Wednesday or Friday (Kiddush HaChodesh 7:1). Kernel-checked; proof by unfolding the dechiyot and omega. Also Hebrew.rh_weekday. Axioms: propext, Classical.choice, Quot.sound only (see build log). Note: this is true by construction of the procedure, as in Russinoff (ACL2); the content is that our Lean transcription of 7:1-6 has the property.",
          ClaimLevel.L3_LEAN_VERIFIED, [THM, "lab/experiments/hebrew-calendar/build.log"], [RAMBAM, RUSSINOFF], cert(THM)),
    entry("HEB-b-year-lengths", "Theorem Hebrew.yearLength_legal / yearLength_mem / yearLength_leap_iff: for every year y>=1 a common year has 353, 354 or 355 days and a leap year 383, 384 or 385 (and conversely). Corresponds to Russinoff's ACL2 `legal-year-lengths`. Method: reduce to the molad's weekday (7 cases) and time (omega), no brute force over years. Also Hebrew.rambam_8_10 (the signs of Kiddush HaChodesh 8:10, = Russinoff's `keviyot`). Kernel-checked, standard axioms only.",
          ClaimLevel.L3_LEAN_VERIFIED, [THM, "lab/experiments/hebrew-calendar/build.log"], [RAMBAM, RUSSINOFF], cert(THM)),
    entry("HEB-c-14-keviyot", "Theorem Hebrew.exactly_14_keviyot: (i) every year's (RH weekday, length) is in the explicit list keviyot14 of 14 distinct pairs (at most 14 — as in ACL2), and (ii) each of the 14 occurs: witness years [15,1,4,7,23,26,2,8,14,27,3,6,19,25] checked by kernel `decide` (Hebrew.keviyot_witnesses, keviyot14_occur). Part (ii) is our addition beyond Russinoff 2022. Kernel-checked, standard axioms only.",
          ClaimLevel.L3_LEAN_VERIFIED, [THM, "lab/experiments/hebrew-calendar/build.log"], [RAMBAM, RUSSINOFF, NOVELTY], cert(THM)),
    entry("HEB-d-period", "Theorem Hebrew.keviyah_period / isPeriod_greatPeriod: keviyah (y + 689472) = keviyah y for all y>=1 (689472 = 19*36288 years = 251,827,457 days = 35,975,351 weeks, Hebrew.greatPeriod_arith). Proof: the molad advances by an exact number of weeks and the leap flag is 19-periodic, so fixRH shifts by whole weeks (fixRH_add_weeks). Russinoff proves the analogous statement for year lengths in ACL2; this is the Lean version for the full keviyah. Kernel-checked, standard axioms only.",
          ClaimLevel.L3_LEAN_VERIFIED, [THM, "lab/experiments/hebrew-calendar/build.log"], [RAMBAM, RUSSINOFF, "en.wikipedia.org/wiki/Hebrew_calendar (36,288 Metonic cycles) — see SOURCES.md"], cert(THM)),
    entry("HEB-e-minimality", "Theorem Hebrew.greatPeriod_minimal: no d with 0 < d < 689472 is a period of the keviyah sequence (IsPeriod d := forall y>=1, keviyah (y+d) = keviyah y). Proof: periods are closed under gcd (Euclid, IsPeriod.gcd), so a smaller period would give a proper divisor of 689472 that is a period, hence (via a prime p in {2,3,7,19}) one of 689472/p would be a period; but keviyah (1 + 689472/p) != keviyah 1 for each p, by kernel `decide`. We found no prior formal proof of minimality (Russinoff only proves that 689472 is a period; the 'smallest n' remark there concerns the molad modulo the week). Kernel-checked, standard axioms only.",
          ClaimLevel.L3_LEAN_VERIFIED, [THM, "lab/experiments/hebrew-calendar/build.log"], [RAMBAM, RUSSINOFF, NOVELTY], cert(THM)),
]

if __name__ == "__main__":
    for e in ENTRIES:
        rec = append(e, LEDGER)
        print(rec["attempt_id"], rec["goal_id"], "L%d" % rec["claim_level"])
