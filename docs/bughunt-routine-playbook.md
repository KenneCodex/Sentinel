# Bug Finder and Fixer — Routine Playbook

This playbook defines the method used by the **Bug finder and fixer** routine
listed in `docs/automation-routines.md`. That document defines the routine's
source-state, receipt, and notification contract; this document defines how a
run investigates, interprets, verifies, and reports a result.

The 2026-08-04 run remains a worked example. It independently reproduced one
real defect, but later reconciliation showed that an earlier parallel pull
request had already found the same defect plus two others. That miss is retained
as evidence: inspecting every file is an activity claim, not proof that every
defect was found.

The scheduled routine is distinct from the deterministic `bughunt` job in
`.github/workflows/sentinel-routines.yml`. The job runs on qualifying pushes and
pull requests selected by path filters and checks syntax, compilation, tests,
and whitespace. It cannot replace adversarial inspection of behavior that
existing tests do not cover.

## Run manifest: 2026-08-04

| Field | Value |
|---|---|
| Repository | `KenneCodex/Sentinel` |
| Original base SHA | `e3a0ab3022348590e68350ae0d8a856535a23c9f` |
| Independent discovery commit | `8f8e02b7d117b81f57e7e1f5a243ec63e5f09df2` |
| Initial methodology commit | `9cad12b0676bd13d8a13679014c4025972fbe822` |
| HyperEVE evidence revision | `84ee3b9564aeb65e007320dcba1df103d9d4afd3` |
| Playbook CI-trigger revision | `4ab7cb2fbeac35e8c83cfb43e7bbd38704f9536d` |
| Independent discovery PR | [#32](https://github.com/KenneCodex/Sentinel/pull/32) |
| Parallel earlier PR | [#31](https://github.com/KenneCodex/Sentinel/pull/31) at `384e1b1865c06a96868473d6fbf995126d7734ca` |
| Relationship | Partial duplicate: #31 contains the same `cli-validation.sh` fix plus two additional fixes; #32 contains the unique methodology lineage |
| Prospective canonical executable lineage | PR #31, subject to review and merge |
| Prospective canonical methodology lineage | PR #32 documentation after reconciliation and removal of the duplicate executable commit |
| Exact-head CI for `9cad12b` | Sentinel Scheduled Routines `30912879997`; Shell Script CI `30912879918`; both successful |
| Exact-head CI for `4ab7cb2` | Sentinel Scheduled Routines `30935242278`; Shell Script CI `30935242275`; both successful |

## Scope and authority

The routine may read, inspect, reproduce, patch, test, commit, push, and open a
draft pull request. It must not merge, force-push shared branches, widen
permissions, deploy, or perform another irreversible action merely because the
run is unattended.

The output is a proposal plus evidence. A draft PR, successful local test, or
green CI run proves only the exact surface exercised. It does not prove
exhaustive defect absence, runtime parity on unrelated nodes, or correctness of
unexecuted documentation examples.

## Codec interpretation contract

Codec's role in this method is to preserve meaning while information crosses
human language, repository documentation, workflow configuration, shell code,
API surfaces, and audit records. A term must not silently gain stronger meaning
when translated to another layer.

### Claim classes

Every material statement should be classifiable as one of:

- **Observed** — directly read, executed, or returned by a named source.
- **Derived** — calculated deterministically from observed inputs, with the
  method identified.
- **Interpreted** — a reasoned explanation of observed or derived evidence.
- **Proposed** — a future change, intended lineage, or unexecuted design.
- **Symbolic** — ritual, phase, resonance, or metaphorical framing that carries
  meaning but is not itself runtime evidence.

Do not convert `interpreted`, `proposed`, or `symbolic` statements into
`observed` status through confident wording.

### Translation invariants

1. **Same term, same referent.** Record when `phase`, `state`, `status`,
   `canonical`, `verified`, `ready`, or `complete` refers to a symbolic label,
   document lifecycle, Git state, CI result, or live runtime condition.
2. **Interface names require an adapter map.** A conceptual function, CLI
   command, HTTP endpoint, workflow job, and Python function are not presumed to
   be the same operation merely because their names or purposes resemble one
   another.
3. **Metrics require producers.** A named metric or threshold is operational
   only when its formula, input source, producer, timestamp, and decision rule
   are identified. Otherwise retain it as symbolic or undefined metadata.
4. **Validation has levels.** Syntax/lint is not behavioral verification;
   behavioral verification is not integration validation; integration
   validation is not production certification.
5. **Canonical means selected authority, not oldest or loudest.** Record the
   selection rule, competing lineages, and final merge or supersession receipt.
6. **No silent reconciliation.** Divergent phase labels, APIs, schemas,
   thresholds, or histories remain separate until an explicit mapping or
   authority decision is recorded.

### Run contract header

Before execution, record at least:

```yaml
intent: <bounded task>
base_sha: <exact checkout>
execution_allowed: true|false
ambiguity_allowed: true|false
confidence_cap: 0.0-1.0
process_ref: <routine/playbook version>
input_refs:
  - <file, PR, issue, or artifact locator>
expected_output: <patch, report, receipt, or no-change result>
```

This header separates intent from authority and prevents a descriptive prompt
from being mistaken for permission to merge, deploy, or canonize.

## Step-by-step method

### 1. Synchronize the timeline before searching

Inspect repository history and active parallel work:

```bash
git status
git log --oneline -10
git branch -a
gh pr list --state open --limit 100
gh pr view <relevant-pr> --json number,title,headRefName,baseRefName,commits,files
```

Record the exact base SHA. Search open PRs for paths, functions, interfaces, and
symptoms likely to overlap the review. Classify each relevant lineage as:

- already addressed;
- partial duplicate requiring consolidation;
- independent;
- superseded;
- unresolved pending comparison.

Do not infer PR scope from a remote branch name alone. The 2026-08-04 run missed
PR #31, which already contained the same shell fix and two additional defects.

### 2. Resolve source and interface authority

Before comparing behavior to documentation, identify the authoritative surface
for each claim:

| Claim | Preferred evidence |
|---|---|
| Current code behavior | Exact checkout plus reproduction |
| HTTP API | Registered routes or generated runtime schema |
| CLI behavior | Parser/help output plus execution |
| Workflow behavior | Exact workflow file plus Actions receipt |
| Data contract | Adopted schema plus validation harness |
| Symbolic role or phase | Named lineage artifact; reference-only unless mapped to a runtime producer |

When two documents expose different function or endpoint sets, do not blend them
into a larger imagined API. Record an adapter or mark the relationship
unresolved.

### 3. Inventory the actual surface

```bash
find . -type f -not -path '*/.git/*' | sort
wc -l tools/*.py tests/*.py
```

List every relevant source, test, workflow, schema, and operational document.
Do not substitute a keyword search for an inventory: control-flow and contract
defects often have no `TODO`, `FIXME`, or other textual signature.

### 4. Read each relevant file end-to-end

For a repository of manageable size, read complete files rather than isolated
search excerpts. Check behavior against callers, comments, documentation, data
schemas, workflows, and examples.

Core defect classes include:

- missing or null values used without validation;
- off-by-one bounds, slices, counters, and thresholds;
- missing error handling around I/O, subprocesses, network calls, and parsing;
- races or unsafe shared-state mutation;
- logic that contradicts the function's stated or caller-observed intent;
- incorrect audit, readiness, or status claims;
- documentation whose examples cannot execute as written;
- schema, tokenizer, serialization, or adapter mismatches;
- dormant code whose apparent validity has never been exercised.

Reading every file does not justify saying “no defect exists.” The evidence-bound
wording is: **reviewed; no defect identified during this run**.

### 5. Perform a separate security and trust-boundary pass

Correctness inspection is not enough for automation repositories. Check:

- untrusted issue, PR, dispatch, or network content crossing into shell code;
- GitHub expression interpolation inside `run:` blocks;
- command, JSON, YAML, path, log, and template injection;
- secrets, credentials, tokens, and permission scope;
- third-party Actions pinned to mutable branches or tags;
- unsafe temporary files, replacement, traversal, or symlink behavior;
- audit records that claim success more broadly than the action performed;
- external inputs that can weaken a declared guardrail;
- symbolic or policy language that is treated as executable authorization.

The parallel lineage found a GitHub Actions script-injection path that the
narrower run missed. This security pass is mandatory, not optional hardening.

### 6. Perform a contract and translation pass

Trace each important concept across its representations:

```text
requirement → documentation → schema/API → implementation → test → receipt
```

Flag any transition where:

- a field, endpoint, phase, status, or function disappears;
- two layers tokenize, normalize, serialize, or default values differently;
- parameters are constructed but not passed;
- a conceptual function is described as though it were a registered endpoint;
- an example claims success without a reproducible harness;
- a metric is reported without a producer or timestamp.

Contract drift is a correctness defect even when each isolated file is
syntactically valid.

### 7. Distinguish defects from intentional boundaries

Before patching, determine whether suspicious behavior is:

- a defect;
- an intentional stub or demonstration boundary;
- dormant but deliberately retained;
- a feature request rather than a repair;
- historical or symbolic evidence that should not execute.

For example, `multi-host-deployment.sh` explicitly describes its deployment
function as a demonstration framework. Implementing real deployment there
without a separate decision would expand authority rather than fix a bug.

### 8. Reproduce before trusting a static read

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

A reproduction receipt states the exact checkout, environment, command, exit
code, and observed output shape.

### 9. Reconcile the finding against parallel lineages

Before writing or publishing a patch, compare the finding with active PRs and
recent commits. If another lineage already fixes it:

- avoid creating a competing canonical implementation;
- determine whether the new run adds stronger reproduction, tests, or method;
- preserve independent rediscovery as evidence;
- route unique additions into a follow-up branch or consolidation PR.

Independent rediscovery is valuable evidence of reproducibility, but it does not
need a second merge of the same code change.

### 10. Isolate the full root cause

Confirm every condition required to produce the failure. For the validation
bug:

1. `check_command()` returns `1` for a missing required tool;
2. required-tool callers invoked it as a bare statement;
3. no `if`, `&&`, or `||` consumed that status;
4. the script runs under `set -e`.

A patch aimed only at the symptom, such as removing `set -e`, would weaken other
failure handling and target the wrong layer.

### 11. Apply the smallest root-cause fix

Prefer a narrow change that preserves intended behavior. In this case, adding
`|| true` to required-tool checks lets the sweep continue while the existing
counter still records the failure and the final process status remains nonzero.
Document non-obvious control-flow safeguards so a future cleanup does not remove
them as apparent noise.

### 12. Re-verify the same failure and broader gates

Run the exact reproduction against the patched state and verify the full outcome
shape, not merely the absence of a crash:

```bash
PATH="$SCRATCH/fakebin" bash ./cli-validation.sh 2>&1 | tail -40
bash -n cli-validation.sh
python3 -m pip install -q -r requirements-dev.txt
python3 -m pytest -q
```

Run ShellCheck and repository-native CI when available. Record unavailable tools
or skipped surfaces explicitly. A previous-head receipt does not verify a later
head.

### 13. Clean verification artifacts

Remove scratch directories and audit files created only by reproduction. Before
committing:

```bash
git status --porcelain
```

The output should contain only intended source, test, workflow, and documentation
changes.

### 14. Commit with lineage and evidence

The commit message should include:

- root cause;
- reproduction;
- behavior preserved by the fix;
- source routine or agent provenance;
- known overlap with another PR or commit;
- claim class for any unverified interpretation.

Do not wait until review to disclose a partial duplicate.

### 15. Open a draft PR from the actual diff

Populate the repository template from the committed change. State what was and
was not tested. If the PR later gains another commit or change class, update the
PR body so it continues to describe the actual diff.

A draft PR is a proposal and locator. It is not a final archival identifier;
record the final merge SHA and disposition when the lineage closes.

### 16. Drive the PR and resolve the future-state fork

Stay attached to CI, review, and overlap changes. Possible outcomes are:

- merge as canonical;
- rebase and drop duplicated commits;
- consolidate unique changes into another PR;
- close as superseded while preserving its evidence;
- revise after contradictory later observation.

For the 2026-08-04 lineages, the intended checkpoint is:

1. review and merge PR #31 as the broader executable lineage;
2. rebase PR #32 onto the resulting `main`;
3. drop duplicate shell-fix commit `8f8e02b`;
4. retain corrected methodology documentation and workflow trigger;
5. rerun CI against the new exact head;
6. record final merge SHAs in this manifest.

### 17. Notify actionably

Because the routine is unattended, send a notification that states:

- what was found;
- what changed;
- where the evidence and PR are;
- whether another lineage overlaps;
- which statements remain interpreted or proposed;
- what human decision or next action remains.

A notification is an index to evidence, not a replacement for the receipt.

## Reusable checklist

1. Write the bounded run contract and record the exact base SHA.
2. Inspect recent commits and all open PRs for overlapping paths or symptoms.
3. Resolve source authority and map conceptual names to actual interfaces.
4. Inventory the complete relevant file surface.
5. Read each relevant file end-to-end.
6. Run correctness, security, and contract/translation passes.
7. Separate defects from stubs, dormant components, features, archives, and symbolic layers.
8. Reproduce the suspected failure in isolation and against the real code.
9. Reconcile the finding against parallel PR and commit lineages.
10. Establish the complete root cause.
11. Apply the smallest root-cause fix.
12. Re-run the same reproduction and broader project gates.
13. Remove verification artifacts and confirm the intended diff.
14. Commit with evidence, provenance, claim class, and overlap disclosure.
15. Open or update a draft PR so its body matches the actual diff.
16. Drive the lineage to merge, consolidation, supersession, or explicit closure.
17. Notify with the result, receipt, overlap state, and next decision.

## Worked example: evidence-bounded record

| Step | Artifact or observation |
|---|---|
| Defect independently found | `cli-validation.sh`: a required `check_command()` returned `1`; as a bare statement under `set -e`, it ended the sweep before later checks, the audit log, and the summary |
| Reproduction | A scratch `PATH` omitted `awk`; the script stopped immediately after reporting the missing required tool |
| Narrow fix | `|| true` at required-tool call sites, preserving recorded failure and final nonzero status while allowing the full sweep to finish |
| Local verification | Same reproduction reached the full summary; `bash -n` passed; `pytest -q` reported 40 passing tests |
| Repository-native verification | PR #32 head `9cad12b` completed Sentinel Scheduled Routines `30912879997` and Shell Script CI `30912879918`; later head `4ab7cb2` completed runs `30935242278` and `30935242275` |
| Parallel lineage discovered during review | PR #31, created earlier from the same base, contained the same shell fix plus a GitHub Actions injection fix and a JSON batch-processing fix |
| Coverage correction | Files were read during the run, but at least two defects were not identified. The record therefore says “reviewed; no defect identified during this run,” not “no defect found” |
| Translation correction | “Green,” “verified,” and “canonical” are now scoped: green names exact CI receipts; verified names exercised surfaces; canonical remains proposed until the lineage decision is merged |
| Lineage disposition | Preserve PR #32 as independent rediscovery and methodology evidence; use PR #31 as the prospective canonical executable lineage; rebase PR #32 and drop its duplicate code commit after #31 resolves |
| Intentional boundary | `multi-host-deployment.sh`'s documented demonstration stub remained unchanged pending a separate authority decision |

## Evidence rule

Observed state outranks narration. A run may claim what it inspected,
reproduced, changed, and verified. It may not convert those facts into exhaustive
defect absence or live-runtime readiness without a separately defined and
satisfied completeness standard.

Symbolic framing may guide interpretation and continuity, but operational claims
must resolve to named producers, interfaces, formulas, exact revisions, and
receipts.