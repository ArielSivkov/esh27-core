"""ESH27 Lab orchestrator: goal bank -> agents -> verifier -> ledger.

Stdlib only. The `anthropic` SDK is optional and imported lazily, only when a
real (non-dry) agent call is made.
"""

__version__ = "0.1.0"
