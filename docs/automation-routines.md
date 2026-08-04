# Sentinel Automation Routines and Notification Contract

This document defines the repository-owned contract for scheduled Sentinel routines. It exists to prevent an unavailable source from being reported as an empty queue and to make every notification carry a verifiable execution state.

## Canonical source

- Repository: `KenneCodex/Sentinel`
- Issue source: GitHub Issues for the repository above
- Supported access paths:
  - GitHub connector with access to the repository
  - A checked-out repository with authenticated `gh`
  - GitHub Actions using `GITHUB_TOKEN`

A routine must resolve its source before performing work. Airtable governance and pattern registries are not substitutes for GitHub Issues unless a routine is explicitly reconfigured to name a specific base and table.

## Routine inventory

| Routine | Purpose | Required source | Expected output |
|---|---|---|---|
| Bug finder and fixer | Inspect code and tests for actionable defects; propose or apply scoped fixes | Repository contents and validation tools | Pass, findings, fix receipt, or blocked state |
| Daily issue triage | Review open issues and classify Bug, Feature, Improvement, and Question work | GitHub Issues | Counts, priorities, unclassified items, or reachable-empty |
| System health check | Verify repository, issue source, credentials, workflows, and notification path | Repository metadata plus issue endpoint | Component states and blockers |

The workflow in `.github/workflows/sentinel-routines.yml` provides a repository-local fallback and manual dispatch target for these routines.

See [`docs/bughunt-routine-playbook.md`](bughunt-routine-playbook.md) for the
step-by-step method behind the "Bug finder and fixer" row above, including a
worked example.

## Source-state vocabulary

Every run must emit exactly one source state:

- `reachable-empty` — the source was queried successfully and returned no matching items.
- `reachable-items` — the source was queried successfully and returned one or more items.
- `unauthorized` — the source exists, but the active credential cannot read it.
- `unavailable` — the source could not be resolved or contacted.
- `partial` — only some required sources were checked; the result must not be presented as complete.

`reachable-empty` is a valid triage result. `unauthorized`, `unavailable`, and `partial` are execution failures or degraded states, not empty queues.

## Notification contract

Each notification must include:

1. Routine name
2. Repository or named source
3. Source state
4. Result state: `pass`, `findings`, `fixed`, `blocked`, or `failed`
5. Item count where applicable
6. A receipt such as a workflow run, commit SHA, PR, issue, or audit artifact
7. The next required action when blocked

Notifications must not claim delivery when a branch or commit exists only in a sandbox. A remote branch SHA or PR URL is required for a delivered-code receipt.

### Default delivery

The workflow always writes a GitHub Actions job summary. This is the baseline receipt even when no external notification endpoint is configured.

### Optional webhook delivery

Set the repository Actions secret `SENTINEL_NOTIFICATION_WEBHOOK` to a Slack-compatible incoming webhook URL. The notification job sends a compact text payload after every run. If the secret is absent, the workflow succeeds in `summary-only` mode and records that state in the job log.

## Credential separation

Do not infer one execution path's authority from another:

- GitHub connector permissions apply to connector calls.
- `GITHUB_TOKEN` permissions apply to a specific Actions workflow run.
- A Claude or other sandbox token applies only inside that sandbox.
- Local `git` or `gh` credentials apply only to that checkout/session.

A connector reporting `push: true` does not prove a separate sandbox can push. Each routine must test the credential it actually uses.

## External scheduler prompt requirements

Claude or another external scheduler should be configured with all of the following:

- Explicit repository: `KenneCodex/Sentinel`
- Explicit GitHub connector or checkout binding
- The routine-specific task
- The source-state vocabulary above
- Instruction to distinguish `reachable-empty` from source failure
- Instruction to include receipts in notifications
- A fallback to dispatch `sentinel-routines.yml` when direct repository inspection is unavailable

## Acceptance checks

A corrected deployment should demonstrate:

- Daily issue triage reports `reachable-empty` when no issues exist.
- The health check reports `unauthorized` when its active credential receives a 401 or 403.
- The bughunt reports deterministic validation counts.
- Every run produces a GitHub job summary.
- A configured webhook receives the same repository, source, and result states.
- No routine substitutes an unrelated Airtable base for GitHub Issues.
