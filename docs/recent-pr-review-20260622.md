# Recent Pull Request Review — Line Numbering Readiness

Date: 2026-06-22
Repository: `KenneCodex/Sentinel`
Branch: `docs/repo-wide-line-numbers-20260622`

## Scope

Reviewed recent pull requests before instituting repository-wide line-numbered document review. The goal was to identify conflicts, conventions, and audit risks relevant to adding a line-numbering policy and tool.

## Reviewed PRs

| PR | Title | Line-numbering impact |
| --- | --- | --- |
| #13 | `config: update default phase to Phase 19 and fix health_check in sentinel_client_update.sh` | Runtime/config oriented. No direct conflict. Health-check changes increase need for citable review lines in future operational docs. |
| #12 | `scripts: add --summary mode to ai-task-prioritization.sh and update docs` | Adds script behavior and documentation. Compatible with line-numbered review copies. Future script docs should cite generated line views. |
| #11 | `msq-idler: add content pack, event schemas, 384-bin hashing, and bounded bandit policy` | Adds structured artifacts. JSON/event schemas should not be manually line-prefixed, but generated numbered views are useful for review. |
| #9 | `tools: add 384-bin harness for void/occupancy diagnostics + audit JSONL` | Audit JSONL should remain machine-readable. Use generated numbered sidecars for human review. |
| #8 | `docs: add game starter asset mapping guide` | Documentation-oriented and directly benefits from generated line-numbered review copies. |
| #4 | `scripts: harden sentinel_client_update.sh and add REVIEW.md` | Security/reliability review noted secret handling and CI gaps. Line-numbered review improves follow-up traceability. |

## Findings

1. No open PRs were found during this review window.
2. Recent work is mixed across docs, shell scripts, schemas, audit JSONL, and runtime configuration.
3. Repo-wide in-place line prefixes would be risky for scripts, JSON, YAML, and machine-readable artifacts.
4. Sidecar numbered copies are the safest default because they improve citation without changing executable or structured files.
5. In-place numbering should be reserved for sealed audit snapshots or explicitly numbered review exports.

## Recommendation

Adopt `docs/line-numbering-policy.md` and `tools/add_line_numbers.py` as the repo-wide standard.

Default command:

```bash
python tools/add_line_numbers.py --root . --output .line-numbered
```

Sentinel classification:

```text
Pattern: PAT-SENTINEL-DOC-LINE-NUMBERS-001
Risk: Low
Mode: Documentation governance
Runtime impact: None
Review impact: Positive
```
