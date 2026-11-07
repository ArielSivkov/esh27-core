"""The five foundations (חמשת היסודות) of ESH27 Lab, as data + an auditor.

Human-readable charter: ../docs/foundations.md. Keep both in sync.

Each foundation is enforced at every layer:
  * agents       — injected into every system prompt (agents.FOUNDATIONS_PROMPT)
  * ledger       — fields `sources`, `review`, `approved_by`, outcome "teiku"
  * orchestrator — `python -m orchestrator.run --audit` reports violations
  * site / book  — shown to readers; nothing is called "proved" below L3
  * people       — outward actions need a named human approver

`audit(entry)` is deliberately *non-blocking* for historical entries: it reports.
The only hard rules live in ledger.validate (L3 needs a certificate; publishing
needs a human approver).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Foundation:
    key: str
    he: str
    source: str
    en: str
    rule: str


FOUNDATIONS: tuple[Foundation, ...] = (
    Foundation(
        "not-in-heaven", "לא בשמים היא", "בבא מציעא נט ע\"ב (תנורו של עכנאי)",
        "Verification over authority",
        "No claim is accepted because of who said it — not a famous name, not a model, "
        "not a 'voice from heaven'. Only evidence counts: a Lean proof or a checkable certificate.",
    ),
    Foundation(
        "in-the-name", "בשם אומרו", "אבות ו, ו; מגילה טו ע\"א",
        "Provenance and attribution",
        "Every claim carries where it came from (paper, DOI, arXiv id, run, file) and who "
        "produced it (human, agent, model). Credit prior work. Unsourced = unusable.",
    ),
    Foundation(
        "i-do-not-know", "למד לשונך לומר איני יודע", "ברכות ד ע\"א",
        "Honest uncertainty",
        "Say 'I don't know'. 'Teiku' (unresolved) is a legitimate outcome. Mark unverified "
        "facts [לא אומת]. Never use the words proved/solved/new below the level that earns them.",
    ),
    Foundation(
        "chavruta", "או חברותא או מיתותא", "תענית כג ע\"א",
        "Adversarial pairing",
        "No result stands alone. Every L2+ result faces a makshan (challenger: agent or human) "
        "whose objections (kushyot) and their answers are recorded. The formal statement is "
        "checked by a second party — the #1 failure mode is proving the wrong statement.",
    ),
    Foundation(
        "servant-not-master", "עבד ולא אדון", "בראשית יא, ד (מגדל בבל: \"ונעשה לנו שם\")",
        "Human sovereignty, against Babel",
        "AI proposes; humans decide. Any outward action (publish, send, deploy, spend) needs a "
        "named human approver. We build to serve truth and people, not 'to make a name for ourselves': no hype.",
    ),
)

FOUNDATIONS_PROMPT = "The five foundations of ESH27 Lab (binding on every agent):\n" + "\n".join(
    f"{i}. {f.he} ({f.en}; {f.source}): {f.rule}" for i, f in enumerate(FOUNDATIONS, 1)
)

# Outcomes. "teiku" = honestly unresolved (foundation 3).
OUTCOMES = ("pending", "success", "partial", "failed", "refuted", "teiku")

# Methods that act on the outside world (foundation 5).
OUTWARD_METHODS = ("publish", "announce", "deploy", "send", "post", "spend")

# Headline language that claims more than evidence below L3 can support (foundation 3).
# Descriptive uses ('lemma X is proved in Lean') are fine; self-congratulation is not.
_OVERCLAIM = re.compile(
    r"\b(we (have )?prov(e|ed)|(is|was|has been|we) solved|first ever|world[- ]first|breakthrough|new record)\b"
    r"|הוכחנו|פתרנו|פריצת דרך|לראשונה בעולם|שיא עולם",
    re.I,
)
# Phrases that *deny* a claim are fine ("not proved", "NOT DONE").
_NEGATED = re.compile(r"\b(not|never|no|un)[-\s]*(yet\s+)?(proved|proven|solved)\b|לא הוכח", re.I)


def _level(e: dict) -> int:
    try:
        return int(e.get("claim_level", 0))
    except (TypeError, ValueError):
        return 0


def audit(e: dict) -> list[tuple[str, str]]:
    """Return [(foundation_key, message)] for one ledger entry. Empty = clean."""
    out: list[tuple[str, str]] = []
    lvl = _level(e)
    cert = e.get("certificate") or {}

    # 1. not-in-heaven: authority is not evidence.
    if lvl >= 3 and not cert.get("verified"):
        out.append(("not-in-heaven", f"L{lvl} without a verified certificate"))
    if e.get("method") == "llm-call" and lvl > 0 and not cert.get("verified"):
        out.append(("not-in-heaven", "raw model output above L0 without verification"))

    # 2. in-the-name: provenance + attribution.
    if not e.get("agent"):
        out.append(("in-the-name", "no attribution (agent/human missing)"))
    if lvl >= 1 and not (e.get("sources") or e.get("artifacts") or cert.get("path")):
        out.append(("in-the-name", f"L{lvl} claim with no sources/artifacts"))

    # 3. i-do-not-know: no overclaiming below L3.
    text = str(e.get("summary", ""))
    if lvl < 3 and _OVERCLAIM.search(_NEGATED.sub("", text)):
        out.append(("i-do-not-know", f"overclaiming language at L{lvl}"))
    if e.get("outcome") and e.get("outcome") not in OUTCOMES:
        out.append(("i-do-not-know", f"unknown outcome {e.get('outcome')!r}"))

    # 4. chavruta: L2+ needs a recorded challenger.
    review = e.get("review") or {}
    if lvl >= 2 and not review.get("makshan"):
        out.append(("chavruta", f"L{lvl} result without a recorded makshan review"))

    # 5. servant-not-master: outward actions need a human.
    if e.get("method") in OUTWARD_METHODS and not e.get("approved_by"):
        out.append(("servant-not-master", f"outward action '{e.get('method')}' without approved_by"))
    return out


def audit_all(entries: list[dict]) -> dict[str, list[tuple[str, str]]]:
    return {e.get("attempt_id", f"#{i}"): v for i, e in enumerate(entries) if (v := audit(e))}
