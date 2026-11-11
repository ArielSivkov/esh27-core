# EshLab — Lean 4 trust kernel

This Lake project is the **only** place where a claim of level **L3 (Lean-verified)** can come from.
LLM output is untrusted until `lake build` accepts it. See `../docs/architecture.md`.

## Layout

| Path | Contents |
|---|---|
| `lakefile.toml` | package `EshLab`, requires Mathlib |
| `lean-toolchain` | Lean version — **must equal Mathlib's** `lean-toolchain` |
| `EshLab/Basic.lean` | warm-up theorems, fully proved (style reference for agents) |
| `EshLab/Targets/*.lean` | open problems stated as `def … : Prop` — **statements only, no `sorry`** |
| `EshLab/Solved/` (future) | proved results, one file per goal id (`G0xx_*.lean`) |

## Build

```bash
# install elan first: https://github.com/leanprover/elan
cd lean
lake update            # resolves mathlib, writes lake-manifest.json
cp .lake/packages/mathlib/lean-toolchain ./lean-toolchain   # keep versions in sync
lake exe cache get     # download prebuilt Mathlib oleans
lake build
```

`lean-toolchain` ships as a placeholder (`v4.24.0`). Before relying on results, pin
`rev` in `lakefile.toml` to a Mathlib tag/commit, copy that Mathlib's `lean-toolchain`,
and commit `lake-manifest.json`. The ledger records the manifest hash with every L3 claim.

## Acceptance rules for an L3 certificate

1. `lake build` succeeds on a clean checkout with the pinned manifest.
2. No `sorry`, `admit`, `axiom`, `native_decide`, `implemented_by`, or `@[extern]` in the proof file
   (`native_decide` is allowed only if the claim is explicitly marked as trusting the compiler).
3. `#print axioms EshLab.<theorem>` lists at most `propext`, `Classical.choice`, `Quot.sound`.
4. The theorem's statement is **syntactically identical** to the human-reviewed target in
   `EshLab/Targets/` (the proof file must `import` it and prove `EshLab.Targets.<Name>`,
   not a restated copy).
5. Each `Targets` file carries `example`s that sanity-check the encoding on small cases.
