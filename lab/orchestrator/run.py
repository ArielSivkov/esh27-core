"""CLI entry point.

    python -m orchestrator.run --list
    python -m orchestrator.run --next
    python -m orchestrator.run --dry-run G001
    python -m orchestrator.run --run G001 --agent literature-agent   # needs ANTHROPIC_API_KEY
    python -m orchestrator.run --ledger-check
"""

from __future__ import annotations

import argparse
import os
import sys

from . import config, ledger
from .agents import ROLES, build_task_prompt, plan_for
from .goals import find, load_goals, pick_next, rank


def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def cmd_list(goals, show_all: bool) -> None:
    rows = rank(goals, include_closed=show_all)
    print(f"{'id':<8} {'score':>6}  {'tier':<4} {'status':<12} {'owner':<19} title")
    print("-" * 90)
    for g in rows:
        print(f"{g.id:<8} {g.score():>6.3f}  {g.tier:<4} {_trunc(g.status, 12):<12} "
              f"{_trunc(g.owner_agent, 19):<19} {_trunc(g.title, 40)}")
    closed = len(goals) - len(rank(goals))
    print(f"\n{len(rows)} goals shown ({closed} closed{' hidden' if not show_all else ''}).")


def cmd_next(goals) -> None:
    g = pick_next(goals)
    if g is None:
        print("No open goals.")
        return
    print(f"NEXT: {g.id} - {g.title}")
    print(f"  score={g.score():.3f} (tractability={g.tractability:.2f}, "
          f"readiness={g.readiness:.2f}, progress={g.progress:.0%}, tier={g.tier or '?'})")
    print(f"  owner: {g.owner_agent or '-'}   field: {g.field or '-'}")


def cmd_dry_run(goal, ledger_path, show_prompts: bool) -> None:
    print(f"DRY RUN for {goal.id}: {goal.title}")
    print(f"model: {config.DEFAULT_MODEL}  (no API calls will be made)")
    prior = ledger.read(ledger_path, goal.id)
    print(f"ledger: {len(prior)} prior attempts, best level "
          f"{'none' if not prior else 'L' + str(ledger.best_level(ledger_path, goal.id))}\n")
    verifier_line = "[4-verify] verifier (program, not LLM): lake build / drat-trim / exact-arith -> L3"
    for stage, role_name in plan_for(goal):
        if stage.startswith("5-"):
            print(verifier_line)
        role = ROLES[role_name]
        print(f"[{stage}] {role_name}  (may self-claim <= L{int(role.max_self_claim)})")
        print(f"    tools: {', '.join(role.tools)}")
        if show_prompts:
            for line in build_task_prompt(role, goal).splitlines():
                print(f"    | {line}")
    print("\nNothing was written. Use --run GOAL --agent NAME for a real call.")


def cmd_run(goal, agent: str, ledger_path) -> int:
    if agent not in ROLES:
        print(f"unknown agent {agent!r}; choose from {sorted(ROLES)}", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set; use --dry-run.", file=sys.stderr)
        return 2
    try:
        import anthropic  # optional dependency
    except ImportError:
        print("pip install anthropic  (optional dependency)", file=sys.stderr)
        return 2
    role = ROLES[agent]
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=config.DEFAULT_MODEL,
        max_tokens=config.MAX_TOKENS,
        system=role.full_system_prompt(),
        messages=[{"role": "user", "content": build_task_prompt(role, goal)}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    print(text)
    rec = ledger.append(ledger.Attempt(
        goal_id=goal.id, agent=agent, method="llm-call",
        claim_level=ledger.ClaimLevel.L0_IDEA,  # raw LLM output is never above L0 until checked
        summary=text[:2000], outcome="pending", model=config.DEFAULT_MODEL,
    ), ledger_path)
    print(f"\nledger: appended attempt {rec['attempt_id']} at L0 (unverified).", file=sys.stderr)
    return 0


def cmd_audit(ledger_path) -> int:
    """Report, per ledger entry, which of the five foundations it falls short of."""
    from .foundations import FOUNDATIONS, audit_all
    entries = ledger.read(ledger_path)
    bad = audit_all(entries)
    names = {f.key: f.he for f in FOUNDATIONS}
    counts: dict[str, int] = {}
    for aid, issues in bad.items():
        e = next((x for x in entries if x.get("attempt_id") == aid), {})
        print(f"{aid}  {e.get('goal_id', '?')}  L{e.get('claim_level', '?')}")
        for key, msg in issues:
            counts[key] = counts.get(key, 0) + 1
            print(f"    [{names.get(key, key)}] {msg}")
    print(f"\n{len(entries)} entries, {len(bad)} with findings.")
    for f in FOUNDATIONS:
        print(f"  {f.he:<28} {counts.get(f.key, 0)}")
    return 0  # an audit reports; it does not block


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="orchestrator.run", description="ESH27 Lab orchestrator")
    act = p.add_mutually_exclusive_group(required=True)
    act.add_argument("--list", action="store_true", help="rank open goals")
    act.add_argument("--next", action="store_true", help="show the highest-priority open goal")
    act.add_argument("--dry-run", metavar="GOAL_ID", help="print the attack plan, no API calls")
    act.add_argument("--run", metavar="GOAL_ID", help="call one agent on a goal (needs API key)")
    act.add_argument("--ledger-check", action="store_true", help="verify ledger hash chain")
    act.add_argument("--audit", action="store_true", help="audit the ledger against the five foundations")
    p.add_argument("--agent", default="literature-agent", help="agent for --run")
    p.add_argument("--goals", default=str(config.GOALS_CSV), help="path to goals.csv")
    p.add_argument("--ledger", default=str(config.LEDGER_PATH), help="path to ledger.jsonl")
    p.add_argument("--all", action="store_true", help="--list: include closed goals")
    p.add_argument("--prompts", action="store_true", help="--dry-run: print task prompts")
    a = p.parse_args(argv)

    if a.ledger_check:
        ok = ledger.verify_chain(a.ledger)
        print("ledger chain OK" if ok else "LEDGER CHAIN BROKEN")
        return 0 if ok else 1

    if a.audit:
        return cmd_audit(a.ledger)

    try:
        goals = load_goals(a.goals)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if a.list:
        cmd_list(goals, a.all)
        return 0
    if a.next:
        cmd_next(goals)
        return 0
    gid = a.dry_run or a.run
    goal = find(goals, gid)
    if goal is None:
        print(f"error: goal {gid!r} not found", file=sys.stderr)
        return 1
    if a.dry_run:
        cmd_dry_run(goal, a.ledger, a.prompts)
        return 0
    return cmd_run(goal, a.agent, a.ledger)


if __name__ == "__main__":
    sys.exit(main())
