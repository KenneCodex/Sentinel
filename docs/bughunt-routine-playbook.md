# Bug Finder and Fixer — Routine Playbook

This playbook documents the method used by the **Bug finder and fixer** routine
listed in `docs/automation-routines.md`. That document defines the routine's
source-state, receipt, and notification contract; this document defines the
investigative method used to reach a result.

The 2026-08-04 run is retained as a worked example. It successfully reproduced
one real defect, but later reconciliation showed that a parallel earlier pull
request had already found the same defect plus two others. That miss is part of
the record: inspecting every file is an activity claim, not proof that every
defect was found.

The scheduled routine is also distinct from the `bughunt` job in
`.github/workflows/sentinel-routines.yml`. The job is a deterministic gate that
runs on qualifying pushes and pull requests selected by its path filters. It can
check syntax, compilation, tests, and whitespace; it cannot replace adversarial
inspection of behavior that existing tests do not cover.

## Run manifest: 2026-08-04

| Field | Value |
|---|---|
| Repository | `KenneCodex/Sentinel` |
| Base SHA | `e3a0ab3022348590e68350ae0d8a856535a23c9f` |
| Independent discovery commit | `8f8e02b7d117b81f57e7e1f5a243ec63e5f09df2` |
| Methodology commit | `9cad12b0676bd13d8a13679014c4025972fbe822` |
| Independent discovery PR | [#32](https://github.com/KenneCodex/Sentinel/pull/32) |
| Parallel earlier PR | [#31](https://github.com/KenneCodex/Sentinel/pull/31) at `384e1b1865c06a96868473d6fbf995126d7734ca` |
| Relationship | Partial duplicate: #31 contains the same `cli-validation.sh` fix plus two additional fixes; #32 contains the unique methodology document |
| Canonical executable lineage | PR #31, subject to review and merge |
| Canonical methodology lineage | PR #32 documentation after reconciliation and removal of the duplicate executable commit |
| Exact-head CI observed for #32 | Sentinel Scheduled Routines run `30912879997`; Shell Script CI run `30912879918`; both successful |

## Scope and authority

The routine may read, inspect, reproduce, patch, test, commit, push, and open a
draft pull request. It must not merge, force-push shared branches, widen
permissions, deploy, or perform another irreversible action merely because the
run is unattended.

The output is a proposal plus evidence. A draft PR, successful local test, or
green CI run proves only the surface actually exercised; it does not prove
exhaustive defect coverage or runtime parity on unrelated nodes.

## Step-by-step method

### 1. Synchronize the timeline before searching

Inspect both repository history and active parallel work:

```bash
git status
git log --oneline -10
git branch -a
gh pr list --state open --limit 100
gh pr view <relevant-pr> --json number,title,headRefName,baseRefName,commits,files
```

Record the exact base SHA. Search open PRs for paths, functions, and symptoms
likely to overlap the area under review. Classify each relevant lineage as:

- already addressed;
- partial duplicate requiring consolidation;
- independent;
- superseded;
- unresolved pending comparison.

Do not infer PR scope from a remote branch name alone. The 2026-08-04 run missed
PR #31, which already contained the same shell fix and two additional defects.

### 2. Inventory the actual surface

```bash
find . -type f -not -path '*/.git/*' | sort
wc -l tools/*.py tests/*.py
```

List every relevant source, test, workflow, schema, and operational document.
Do not substitute a keyword search for an inventory: control-flow defects often
have no `TODO`, `FIXME`, or other textual signature.

### 3. Read each relevant file end-to-end

For a repository of manageable size, read complete files rather than isolated
search excerpts. Check behavior against callers, comments, documentation, data
schemas, and workflow assumptions.

Core defect classes include:

- missing or null values used without validation;
- off-by-one bounds, slices, counters, and thresholds;
- missing error handling around I/O, subprocesses, network calls, and parsing;
- races or unsafe shared-state mutation;
- logic that contradicts the function's stated or caller-observed intent;
- incorrect audit or status claims;
- dormant code whose apparent validity has never been exercised.

Reading every file does not justify saying “no defect exists.” The evidence-bound
wording is: **reviewed; no defect identified during this run**.

### 4. Perform a separate security and trust-boundary pass

Correctness inspection is not enough for automation repositories. Check:

- untrusted issue, PR, dispatch, or network content crossing into shell code;
- GitHub expression interpolation inside `run:` blocks;
- command, JSON, YAML, path, or log injection;
- secrets, credentials, tokens, and permission scope;
- third-party Actions pinned to mutable branches or tags;
- unsafe temporary files, replacement, traversal, or symlink behavior;
- audit records that claim success more broadly than the action performed;
- external inputs that can weaken a declared guardrail.

The 2026-08-04 parallel lineage found a GitHub Actions script-injection path that
the narrower run missed. This security pass is therefore mandatory, not
optional hardening.

### 5. Distinguish defects from intentional boundaries

Before patching, determine whether the suspicious behavior is:

- a defect;
- an intentional stub or demonstration boundary;
- dormant but deliberately retained;
- a feature request rather than a repair;
- historical evidence that should not execute.

For example, `multi-host-deployment.sh` explicitly describes its deployment
function as a demonstration framework. Implementing real deployment there
without a separate decision would expand authority rather than fix a bug.

### 6. Reproduce before trusting a static read

First isolate language or platform semantics, then reproduce against the actual
code. For the `set -e` interaction:

```bash
bash -c '
set -e
f() { return 1; }
f
echo "after f"
'
echo "exit code: $?"
```

Then create a throwaway `PATH` that omits one required tool without modifying the
host:

```bash
SCRATCH=/path/to/scratchpad
mkdir -p "$SCRATCH/fakebin"
for c in bash sh cat grep sed git curl date mkdir uname hostname find head; do
  ln -sf "$(command -v "$c")" "$SCRATCH/fakebin/$c"
done
PATH="$SCRATCH/fakebin" bash ./cli-validation.sh
echo "exit code: $?"
```

A reproduction receipt should state the exact checkout, environment, command,
exit code, and observed output shape.

### 7. Reconcile the finding against parallel lineages

Before writing or publishing a patch, compare the finding with active PRs and
recent commits. If another lineage already fixes it:

- avoid creating a competing canonical implementation;
- determine whether the new run adds stronger reproduction, tests, or method;
- preserve independent rediscovery as evidence;
- route unique additions into a follow-up branch or consolidation PR.

Independent rediscovery is valuable evidence of reproducibility, but it does not
need a second merge of the same code change.

### 8. Isolate the full root cause

Confirm every condition required to produce the failure. For the validation
bug:

1. `check_command()` returns `1` for a missing required tool;
2. required-tool callers invoked it as a bare statement;
3. no `if`, `&&`, or `||` consumed that status;
4. the script runs under `set -e`.

A patch aimed only at the symptom, such as removing `set -e`, would weaken other
failure handling and target the wrong layer.

### 9. Apply the smallest root-cause fix

Prefer a narrow change that preserves intended behavior. In this case, adding
`|| true` to required-tool checks lets the sweep continue while the existing
counter still records the failure and the final process status remains nonzero.
Document non-obvious control-flow safeguards so a future cleanup does not remove
them as apparent noise.

### 10. Re-verify the same failure and broader gates

Run the exact reproduction against the patched state and verify the full outcome
shape, not merely the absence of a crash:

```bash
PATH="$SCRATCH/fakebin" bash ./cli-validation.sh 2>&1 | tail -40
bash -n cli-validation.sh
python3 -m pip install -q -r requirements-dev.txt
python3 -m pytest -q
```

Run ShellCheck and repository-native CI when available. Record unavailable tools
or skipped surfaces explicitly.

### 11. Clean verification artifacts

Remove scratch directories and audit files created only by the reproduction.
Before committing:

```bash
git status --porcelain
```

The output should contain only intended source, test, workflow, and documentation
changes.

### 12. Commit with lineage and evidence

The commit message should include:

- the root cause;
- the reproduction;
- the behavior preserved by the fix;
- the source routine or agent provenance;
- any known overlap with another PR or commit.

Do not wait until review to disclose a partial duplicate.

### 13. Open a draft PR from the actual diff

Populate the repository template from the committed change. State what was and
was not tested. If the PR later gains a second commit or new change class, update
the PR body so it continues to describe the actual diff.

A draft PR is a proposal and a locator. It is not a final archival identifier;
record the final merge SHA and disposition when the lineage closes.

### 14. Drive the PR and resolve the future-state fork

Stay attached to CI, review, and overlap changes. The possible outcomes are:

- merge as canonical;
- rebase and drop duplicated commits;
- consolidate unique changes into another PR;
- close as superseded while preserving its evidence;
- revise after a contradictory later observation.

For the 2026-08-04 lineages, the intended checkpoint is:

1. review and merge PR #31 as the broader executable lineage;
2. rebase PR #32 onto the resulting `main`;
3. drop the duplicate `8f8e02b` shell-fix commit;
4. retain the corrected methodology documentation;
5. rerun CI against the new exact head;
6. record final merge SHAs in this manifest.

### 15. Notify actionably

Because the routine is unattended, send a notification that states:

- what was found;
- what changed;
- where the evidence and PR are;
- whether another lineage overlaps;
- what human decision or next action remains.

A notification is an index to evidence, not a replacement for the receipt.

## Reusable checklist

1. Record the exact base SHA and clean working-tree state.
2. Inspect recent commits and all open PRs for overlapping paths or symptoms.
3. Inventory the complete relevant file surface.
4. Read each relevant file end-to-end.
5. Run both correctness and security/trust-boundary passes.
6. Separate defects from stubs, dormant components, features, and archives.
7. Reproduce the suspected failure in isolation and against the real code.
8. Reconcile the finding against parallel PR and commit lineages.
9. Establish the complete root cause.
10. Apply the smallest root-cause fix.
11. Re-run the same reproduction and broader project gates.
12. Remove verification artifacts and confirm the intended diff.
13. Commit with evidence, provenance, and overlap disclosure.
14. Open or update a draft PR so its body matches the actual diff.
15. Drive the lineage to merge, consolidation, supersession, or explicit closure.
16. Notify with the result, receipt, overlap state, and next decision.

## Worked example: evidence-bounded record

| Step | Artifact or observation |
|---|---|
| Defect independently found | `cli-validation.sh`: a required `check_command()` returned `1`; as a bare statement under `set -e`, it ended the sweep before later checks, the audit log, and the summary |
| Reproduction | A scratch `PATH` omitted `awk`; the script stopped immediately after reporting the missing required tool |
| Narrow fix | `|| true` at required-tool call sites, preserving recorded failure and final nonzero status while allowing the full sweep to finish |
| Local verification | Same reproduction reached the full summary; `bash -n` passed; `pytest -q` reported 40 passing tests |
| Repository-native verification | PR #32 head `9cad12b` completed Sentinel Scheduled Routines run `30912879997` and Shell Script CI run `30912879918` successfully |
| Parallel lineage discovered during review | PR #31, created earlier from the same base, contained the same shell fix plus a GitHub Actions injection fix and a JSON batch-processing fix |
| Coverage correction | Files were read during the run, but at least two defects were not identified. The record therefore says “reviewed; no defect identified during this run,” not “no defect found” |
| Lineage disposition | Preserve PR #32 as independent rediscovery and methodology evidence; use PR #31 as the canonical executable lineage; rebase PR #32 and drop its duplicate code commit after #31 is resolved |
| Intentional boundary | `multi-host-deployment.sh`'s documented demonstration stub remained unchanged pending a separate authority decision |

## Evidence rule

Observed state outranks narration. A run may honestly claim what it inspected,
reproduced, changed, and verified. It may not convert those facts into a claim of
exhaustive defect absence without a separately defined and satisfied completeness
standard.
