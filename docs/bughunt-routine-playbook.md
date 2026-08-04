# Bug Finder and Fixer — Routine Playbook

This documents the step-by-step method an agent (or a developer doing the same
sweep by hand) followed to execute the **Bug finder and fixer** routine listed
in `docs/automation-routines.md`, using the 2026-08-04 run as a worked example.
It is a companion to that document, not a replacement: `automation-routines.md`
defines the *contract* (source states, notification fields, receipts); this
document defines the *method* used to actually reach a result.

It is also distinct from the `bughunt` job in `.github/workflows/sentinel-routines.yml`.
That job is a deterministic gate — syntax-check every shell script, byte-compile
every Python file, run the test suite, check for whitespace errors — and it runs
on every push/PR. It cannot find a bug that all of those checks pass on, which is
exactly the class of bug this routine is for: a script that is syntactically
valid, byte-compiles, and has no test covering it, but is still wrong.

## When this routine runs

Configured as a scheduled Claude Code routine against `KenneCodex/Sentinel`,
firing on its own without a live user watching. Because no one is present to
approve risky actions mid-run, the routine is scoped to read/inspect/fix/PR —
never to merge, force-push, or take an action a developer hasn't implicitly
pre-authorized by configuring the routine this way.

## Step-by-step method

### 1. Orient before searching

Before opening any file:

```bash
git status && git log --oneline -10 && git branch -a
```

Confirm the working tree is clean and identify what the last few merged PRs
already touched. Bugs found in a subsystem someone just finished hardening
(three commits ago) are a weaker use of a scheduled run than bugs in code no
one has looked at recently — check the recent log before spending a pass on a
file that was just reviewed.

### 2. Inventory the actual surface

```bash
find . -type f -not -path '*/.git/*' | sort
wc -l tools/*.py tests/*.py
```

List every file, not just the ones a keyword search would surface. This
repository's real bug this run was in a `.sh` file — a keyword search for
"bug"-shaped terms (`null`, `TODO`, `FIXME`) would not have found it, because
the defect was a control-flow interaction (`set -e` plus a bare function call),
not a marked-up code smell.

### 3. Read every file in full, not excerpts

For a codebase this size (~1,900 lines across Python tools/tests and shell
scripts), read each file end-to-end with the `Read` tool rather than grepping
for suspicious patterns. Grepping for `null`/`except:`/`TODO` finds *labeled*
bugs; it misses logic bugs that look like ordinary control flow. The bug this
run — `check_command` returning `1` under `set -e` — has no keyword signature
at all; it only shows up by reading `validate_required_tools()` and asking
"what happens if this specific call fails."

While reading, check each file against the bug classes named in the routine's
brief:

- Null/attribute dereference on a value that can be `None`/missing
- Off-by-one in a loop bound, slice, or index
- Missing error handling on an operation that can fail (I/O, subprocess,
  network, parse)
- Race conditions (shared mutable state touched by more than one path)
- Logic errors: a function's behavior doesn't match its docstring or its
  only caller's assumption about it

For each file, also ask **"is this dead code, a documented stub, or a decoy
before I burn time on it?"** `multi-host-deployment.sh`'s `deploy_environment`
function logs `"Note: This is a framework implementation for demonstration"`
and deliberately does not deploy anything — that is not a bug, and "fixing" it
would mean inventing a deployment implementation nobody asked for. Recognizing
an intentional stub and moving on is part of the method, not a shortcut around
it.

### 4. Don't trust a static read — reproduce it

Reading code tells you what a bug *might* do; running it tells you what it
*does* do. For the `cli-validation.sh` bug, the mechanism (`set -e` aborting on
a bare failing call) is a well-known bash gotcha, confirmed first in isolation:

```bash
bash -c '
set -e
f() { return 1; }
f
echo "after f"
'
echo "exit code: $?"
# -> "after f" never prints; exit code 1
```

Then reproduced against the actual script by building a minimal sandboxed
`PATH` that has every required tool *except* one, so `check_command` hits its
`return 1` branch for real:

```bash
SCRATCH=/path/to/scratchpad
mkdir -p "$SCRATCH/fakebin"
# Symlink every tool the script needs EXCEPT the one you're testing the
# missing-tool path for (here, deliberately omitting awk):
for c in bash sh cat grep sed git curl date mkdir uname hostname find head; do
  ln -sf "$(command -v "$c")" "$SCRATCH/fakebin/$c"
done
PATH="$SCRATCH/fakebin" bash ./cli-validation.sh; echo "EXIT CODE: $?"
```

This is the reusable technique for any "script behaves differently when tool X
is missing/absent" hypothesis: build the minimal `PATH`, don't disable
anything on the real host, and delete the scratch directory afterward.

### 5. Isolate root cause before writing the fix

Confirm *why*, not just *that*. Here: `check_command()` explicitly
`return 1`s when a required tool is missing; every call site in
`validate_required_tools()` invokes it as a bare statement; none of them check
the return value in an `if`/`&&`/`||`; the script runs under `set -e`. All four
facts together produce the abort — dropping any one of them means the fix
targets the wrong layer (e.g., "just remove `set -e`" would silence the abort
but also silence every *other* real failure the script should catch).

### 6. Apply the smallest fix that addresses the root cause

Preferred over larger restructuring: add `|| true` at each of the 8 call sites
in `validate_required_tools()` that pass `required=true`, plus a one-line
comment explaining *why* the `|| true` is there (so a future reader doesn't
mistake it for a copy-paste artifact and delete it). This preserves every
existing behavior — `FAILED_CHECKS` still increments, the final exit code is
still non-zero when a required tool is missing — while letting the rest of the
sweep run to completion.

Calls with `required=false` were left untouched: `check_command` returns `0`
on that path even when the tool is absent, so they were never at risk.

### 7. Verify the fix, not just the absence of an error

Re-run the exact repro from step 4 against the patched script and confirm the
*shape* of the output changed (full summary + audit log produced, not just
"no crash"):

```bash
PATH="$SCRATCH/fakebin" bash ./cli-validation.sh 2>&1 | tail -40
```

Then run the project's broader gates so the fix hasn't regressed anything
outside its own file:

```bash
bash -n cli-validation.sh                 # syntax
python3 -m pip install -q -r requirements-dev.txt
python3 -m pytest -q                      # 40 passed
```

`shellcheck` was not installed in the sandbox for this run — noted rather than
skipped silently, since `shell-script-ci.yml` runs it in CI and it should be
run locally when available.

### 8. Clean up what the verification pass created

The repro and test runs write real artifacts (`.audit-logs/cli-validation-*.json`
in this case). Remove anything the *verification* process generated before
committing — `git status --porcelain` should show only the intended file
change, and the scratch `PATH` sandbox directory under the session scratchpad
gets deleted, not committed.

### 9. Commit with the root cause and repro in the message

The commit message states the mechanism (`set -e` + bare failing call), how it
was confirmed (the `awk`-stripped-`PATH` repro), and what the fix preserves
(failure is still recorded and still reflected in the exit code) — enough for
a reviewer to evaluate the fix without re-deriving it from the diff alone.

### 10. Push, then open a draft PR filled from the actual diff

```bash
git push -u origin <branch>
```

Before opening the PR, check for a template (`.github/PULL_REQUEST_TEMPLATE.md`
here) and populate every section from the real change — the template's
sections become the PR body's structure, not a checklist to follow literally.
Sections that ask for things unrelated to the diff (credentials, deployment
steps for a change with no deployment) are answered "N/A" or skipped rather
than invented. The PR is opened as a **draft** — this routine proposes fixes
for review, it does not merge them.

### 11. Subscribe to PR activity and drive it, don't abandon it

After creating the PR, subscribe to its activity and stay attached to it:
diagnose and push a fix for real CI failures, reply to review comments that
need a response, and skip bot noise that requires no action (e.g., a
third-party review bot announcing its own service is sunset). A PR this
routine opened is not "done" until it is merged or closed — the routine's job
includes watching it to that point, not just filing it.

### 12. Notify, don't just log

Because this runs unattended, the result has to reach a person through a
channel they'll actually see (push notification / email), not just sit in a
session transcript nobody opens. The notification should be actionable on its
own: what was found, what changed, where the PR is — enough that someone could
act on it without opening the session.

## Reusable checklist

For the next run of this routine (agent or human):

1. `git status && git log --oneline -10` — orient
2. `find . -type f -not -path '*/.git/*' | sort` — full inventory, not a
   keyword search
3. Read every source file end-to-end; check each against: null/attribute
   deref, off-by-one, missing error handling, race conditions, logic errors
   vs. stated intent
4. Distinguish real bugs from intentional stubs/placeholders before spending
   time on either
5. Reproduce the hypothesized failure before trusting a static read —
   isolate the mechanism in a throwaway one-liner first if it's a language
   gotcha (like `set -e` semantics), then reproduce against the real script
6. Confirm root cause covers every contributing factor, not just the
   symptom
7. Apply the smallest fix that addresses the root cause; comment the
   non-obvious part so it survives the next refactor
8. Re-run the same repro against the fix and confirm the *shape* of the
   outcome changed, then run the project's broader test/syntax/lint gates
9. Delete artifacts the verification pass created; confirm `git status`
   shows only the intended change
10. Commit with root cause + repro in the message
11. Push, open a draft PR from the repo's template populated from the real
    diff
12. Subscribe to the PR and drive it to green / respond to review, skipping
    only genuine no-ops
13. Send an actionable notification — what was found, what changed, where
    the receipt is

## Worked example from this run

| Step | Artifact |
|---|---|
| Bug found | `cli-validation.sh`: `check_command()` returns `1` for a missing required tool; called bare under `set -e`, it aborted the whole validation run at the first missing required tool, skipping every later check, the audit log, and the summary |
| Repro | `PATH` sandbox with `awk` omitted; script died immediately after logging `awk is not installed (REQUIRED)` |
| Fix | `\|\| true` at each `required=true` call site in `validate_required_tools()`, plus an explanatory comment |
| Verification | Same repro re-run (full summary now produced, exit `1` as expected because two checks still legitimately fail in that sandbox); `bash -n`; `pytest -q` (40 passed, unaffected) |
| Receipt | Commit `8f8e02b`, branch `claude/adoring-hopper-2zk1zv`, draft PR [#32](https://github.com/KenneCodex/Sentinel/pull/32) |
| Files reviewed with no fix needed | `tools/msq_bandit_policy.py`, `tools/bin_harness_384.py`, `tools/msq_state.py`, `tools/msq_telemetry.py`, `tools/msq_demo_run.py`, `tools/add_line_numbers.py` (all covered by passing tests, no defect found); `ai-task-prioritization.sh`, `multi-host-deployment.sh`, `sentinel_client_update.sh` (reviewed; `multi-host-deployment.sh`'s deploy stub is an intentional, documented placeholder, not a bug) |
