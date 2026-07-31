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

### Tier 3 — Dormant declarations

These are declared contracts with no enforcing implementation. They are the most
easily missed form of dormancy, because the declaration reads as though it is in
force.

`data/msq/content_pack_v1.json` declares `ai_tuning.guardrails`:

| Guardrail | Declared value | Enforcement |
|---|---|---|
| `min_runs_before_personalization` | `3` | **None.** `choose_arm()` in `tools/msq_bandit_policy.py` never consults `runs_seen`. The field is incremented by `update_arm()` and read by nothing, so personalization begins on run 1. |
| `max_difficulty_step_per_session` | `1` | **None.** No module bounds the magnitude of an applied arm delta. |
| `bounded_changes_only` | `true` | Satisfied structurally — `DEFAULT_ARMS` is a fixed five-arm table — but not asserted anywhere. |
| `no_sensitive_inference` | `true` | Satisfied structurally; the policy state holds only `player_id` and Beta parameters. |

The first two are genuine gaps between declared and actual behavior. They were
left unimplemented here deliberately: `docs/msq_idler/README.md` scopes this
layer to "arm selection only", and the guardrails govern how a *client* applies a
delta, which is outside the repository. The gap is recorded so that whichever
layer consumes the pack knows the enforcement is its responsibility and not
inherited from these tools.

## Summary

- 5 components activated, with CI now executing 13 tests where it previously executed none.
- 1 latent defect found and fixed, uncovered by the act of activation.
- 4 components retained with stated rationale.
- 4 declared guardrails classified: 2 structurally satisfied, 2 recorded as unenforced by design at this layer.
