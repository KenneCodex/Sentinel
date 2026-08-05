# Archivist Admission Gate for Bug-Finder Runs

The scheduled **Bug finder and fixer** routine must pass this gate before it
creates a branch or pull request. The gate exists because an execution event, a
defect, a patch, a pull request, and a merged resolution are different archival
objects. Reproducing an already-known defect is evidence, but it is not a new
defect and does not justify a competing PR.

## Result states

Every semantic bug-finder run emits exactly one durable result:

| Result | Meaning | PR action |
|---|---|---|
| `CLEAN` | The bounded review completed and identified no unique reproducible defect | Do not open a PR |
| `NEW` | A reproducible defect is not represented by the registry or an open PR marker | A draft PR is allowed |
| `DUPLICATE` | The defect is already represented by canonical or candidate lineage | Suppress the competing PR; attach unique evidence to the canonical lineage |
| `BLOCKED` | The bounded review could not complete because required evidence or execution was unavailable | Do not open a PR; report the blocker |

`CLEAN` means **no defect identified during the recorded bounded run**. It is not
a proof that the repository contains no defects.

## Stable defect identity

`tools/archivist_bug_admission.py` computes a SHA-256 fingerprint over these
normalized fields:

```json
{
  "repository": "KenneCodex/Sentinel",
  "component": "cli-validation.sh",
  "failure_class": "premature_exit",
  "trigger": "required command missing under set -e",
  "affected_symbol": "validate_required_tools",
  "normalized_root_cause": "unguarded nonzero function return"
}
```

The observed base commit is deliberately excluded from the defect fingerprint.
The same defect observed on a later commit remains the same defect; the base SHA
is retained separately in the run receipt.

A `NEW` receipt returns two markers that must be copied into the draft PR body:

```text
Archivist-Defect-ID: BUG-XXXXXXXXXXXX
Archivist-Fingerprint: <64-character SHA-256>
```

Future runs can identify the open lineage from either marker without depending
on title similarity or agent prose.

## Required pre-PR sequence

1. Record the exact repository and base SHA.
2. Inspect recent commits, open PRs, and active branches.
3. Reproduce the candidate defect.
4. Write a candidate JSON document with the five identity fields and bounded
   evidence.
5. Export open PR metadata to JSON when available.
6. Run the admission gate.
7. Preserve the generated receipt.
8. Open a draft PR only when `result` is `NEW` and `pr_allowed` is `true`.
9. Send the receipt's notification message to the configured phone, email, or
   webhook channel.

## CLI examples

### New or duplicate candidate

```bash
python3 tools/archivist_bug_admission.py \
  --run-id RUN-BUGHUNT-20260805-001 \
  --repository KenneCodex/Sentinel \
  --base-sha "$(git rev-parse HEAD)" \
  --candidate /tmp/candidate.json \
  --registry data/bughunt/defect_registry_v1.json \
  --open-prs /tmp/open-prs.json \
  --files-reviewed 24 \
  --tests-executed 40 \
  --reproductions-attempted 1 \
  --output .audit-logs/bughunt/RUN-BUGHUNT-20260805-001.json
```

### Clean run

Omit `--candidate` only after the bounded review and its validation work have
completed:

```bash
python3 tools/archivist_bug_admission.py \
  --run-id RUN-BUGHUNT-20260806-001 \
  --repository KenneCodex/Sentinel \
  --base-sha "$(git rev-parse HEAD)" \
  --files-reviewed 24 \
  --tests-executed 40 \
  --reproductions-attempted 3 \
  --output .audit-logs/bughunt/RUN-BUGHUNT-20260806-001.json
```

### Blocked run

```bash
python3 tools/archivist_bug_admission.py \
  --run-id RUN-BUGHUNT-20260806-002 \
  --repository KenneCodex/Sentinel \
  --base-sha unknown \
  --blocked-reason "Repository checkout unavailable" \
  --output .audit-logs/bughunt/RUN-BUGHUNT-20260806-002.json
```

## Current seeded lineage

`data/bughunt/defect_registry_v1.json` records the `cli-validation.sh`
required-tool/`set -e` defect as one canonical defect entity. PR #31 is the
prospective canonical executable lineage; PRs #32 and #33 are recorded as
duplicate candidates for that defect. The registry does not merge, close, or
approve any PR. It preserves the relationship so the next run cannot count the
same defect again.

## Notification language

Notifications report archival state rather than merely saying that the routine
ran:

```text
NEW: New reproducible defect admitted for a draft pull request.
DUPLICATE: Known defect reproduced; no duplicate pull request was created.
CLEAN: Bug-hunt completed; no unique reproducible defects were identified.
BLOCKED: Bug-hunt blocked: <reason>.
```

A phone notification is a delivery event. The receipt remains the evidence of
what the run actually established.
