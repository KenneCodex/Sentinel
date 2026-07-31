# Dormant Components Audit

A dormant component is one that exists in the repository, is materially complete,
and is never reached by any execution path — no workflow invokes it, no module
imports it, no validator checks it. Dormant components are not the same as dead
code: they usually work, they just carry no signal, so drift accumulates in them
silently.

This audit inventories the dormant surface of the repository, records which items
were activated, and states the disposition of the remainder.

## Method

Every file was cross-referenced against the four workflows in
`.github/workflows/`, the shell entrypoints, and the Python import graph. A
component is classed dormant when the only references to it are documentation.

## Findings

### Tier 1 — Dormant validation (activated)

| Component | Dormancy | Disposition |
|---|---|---|
| `tests/` (4 files) | No workflow ran the suite. `sentinel-routines.yml` byte-compiled Python with `compileall` but never executed a test. | **Activated** — the bughunt sweep now runs `pytest`. |
| `schemas/msq_content_pack_v1.schema.json` | Referenced only by itself. No code or CI validated anything against it. | **Activated** — `tests/test_msq_content_pack.py` validates the shipped pack. |
| `data/msq/content_pack_v1.json` | Authored, schema-valid, loaded by no module. | **Activated** — now covered by schema and cross-reference tests. |

The test suite was the highest-value finding. Three pull requests (#18, #20,
#23) invested in MSQ bandit and telemetry coverage, and none of that coverage
ever executed in CI.

Activating it immediately surfaced a latent defect it had been hiding.

#### Latent defect found on activation

`tests/test_bin_harness_384.py` inserted the repository root into `sys.path` at
module scope. Because pytest collects alphabetically, that insertion happened to
run before `test_msq_bandit_policy.py`, `test_msq_state.py`, and
`test_msq_telemetry.py` — which import from `tools` but never established the
path themselves. The suite therefore passed only as a side effect of collection
order and invocation directory. Run alone, three of the four files failed
collection outright:

```
test_msq_telemetry.py       1 error   (ModuleNotFoundError: tools)
test_msq_bandit_policy.py   1 error   (ModuleNotFoundError: tools)
test_msq_state.py           1 error   (ModuleNotFoundError: tools)
test_bin_harness_384.py     4 passed
```

Fixed by anchoring the path once in `tests/conftest.py` and removing the
incidental insertion. All five files now collect independently.

### Tier 2 — Dormant code and data (retained, not activated)

| Component | Status | Rationale |
|---|---|---|
| `tools/msq_demo_run.py` | Runs correctly; no workflow, test, or doc referenced it. It is the only module that composes state, bandit, and telemetry together. | Retained as the reference integration for the MSQ scaffolding. Its defaults are now pinned to the content pack by test, so pack drift breaks the build rather than the demo. |
| `tools/add_line_numbers.py` | Runs correctly (7 docs processed). `docs/line-numbering-policy.md` declares status "active after merge" and sets a PR requirement, but nothing enforces it. | Retained. The policy is advisory by its own wording ("SHOULD"); mechanising it would change review process, which is a governance decision rather than a code one. |
| `sentinel_client_update.sh` | 244 lines, invoked by no workflow. `cli-validation.sh:171` references it only as a filename in an executable-bit check. | Retained. It is an operator-run client update script; absence from CI is expected for a deployment-side tool. |
| `AI/LocalDex/codex_sync_log.json` | Captured drift telemetry from April 2025, referenced only in `COPILOT_RECOMMENDATIONS.md`. | Retained as a historical artifact. It is data, not code, and carries no drift risk. |

### Tier 3 — Dormant declarations (activated)

These are declared contracts with no enforcing implementation. They are the most
easily missed form of dormancy, because the declaration reads as though it is in
force.

`data/msq/content_pack_v1.json` declares `ai_tuning.guardrails`. All four are now
enforced or asserted in `tools/msq_bandit_policy.py`:

| Guardrail | Declared value | Enforcement |
|---|---|---|
| `min_runs_before_personalization` | `3` | **Enforced.** `choose_arm()` returns the baseline arm until `runs_seen` reaches the declared warmup, so no personalization occurs before then. Previously `runs_seen` was incremented by `update_arm()` and read by nothing, and personalization began on run 1. |
| `max_difficulty_step_per_session` | `1` | **Enforced.** `bound_delta()` clamps every step knob to ±the declared limit. This actively binds today: `C_MORE_HINTS` authors `hint_after_fails: 2` and is served as `1`. |
| `bounded_changes_only` | `true` | **Enforced.** A knob in neither `STEP_KNOBS` nor `SCALE_KNOB_BOUNDS` has no declared bound, so `bound_delta()` refuses it rather than passing an unbounded value to the client. A test asserts every shipped arm knob is covered. |
| `no_sensitive_inference` | `true` | Satisfied structurally; the policy state holds only `player_id` and Beta parameters. |

Guardrail values are read from the pack by `load_guardrails()`, which the demo
runner now calls — so the content pack is consumed at runtime rather than being
inert data. `DEFAULT_GUARDRAILS` mirrors the shipped pack and a test asserts the
two stay identical, so relaxing a bound in the pack cannot silently diverge from
the code that applies it.

A declared value binds only if it is well-typed and inside the range the schema
declares; otherwise that field falls back to its default. This matters because
the pack is plain JSON that nothing validates at runtime — the schema check
lives in the test suite, not in the loader. Without it a pack declaring
`max_difficulty_step_per_session: 9999` would be obeyed, turning the clamp into
a no-op and defeating the guardrail it implements. Falling back to the shipped
default is the fail-safe direction, and `_GUARDRAIL_INT_RANGES` is asserted
against the schema so the loader's copy of those bounds cannot drift.

Two knob kinds are distinguished, because a step count does not describe a
multiplier: step knobs (`spawn_count_per_tick`, `max_locks`, `hint_after_fails`)
are bounded by `max_difficulty_step_per_session`; scale knobs (`base_SE_mult`,
`base_CE_mult`) are bounded by explicit multiplier ranges. Clamping a multiplier
to a step count of 1 would silently neutralise it, which is why the two are not
bounded by the same rule.

`docs/msq_idler/README.md` scopes this layer to "arm selection only". Enforcing
the guardrails here does not widen that scope: the module still only selects an
arm and reports a bounded delta. What changed is that the delta it hands to a
client is now guaranteed to respect the declared bounds, rather than the client
being trusted to apply them.

## Summary

- 5 components activated, with CI now executing 26 tests where it previously executed none.
- 1 latent defect found and fixed, uncovered by the act of activation.
- 4 components retained with stated rationale.
- 4 declared guardrails now enforced or asserted, where 2 previously had no implementation at all.
