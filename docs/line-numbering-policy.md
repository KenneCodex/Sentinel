# Repository-Wide Line Numbering Policy

## Purpose

This repository uses line-numbered document views when performing Sentinel, Archivist, or Codex review. The goal is stable citation, repeatable review, and lower ambiguity when discussing documentation, audit records, operating procedures, and generated reports.

## Scope

Line-numbered review copies SHOULD be generated for text-bearing documentation, including:

- Markdown: `.md`, `.markdown`
- Plain text: `.txt`
- ReStructuredText: `.rst`
- AsciiDoc: `.adoc`

Code files MAY be numbered for review packets, but source files SHOULD NOT be committed with manual line prefixes unless that file is explicitly an audit artifact.

## Standard Format

Generated numbered lines MUST use this format:

```text
L0001 | original line text
L0002 | next original line text
```

The line number is 1-based and zero-padded to four digits by default.

## Repository-Wide Generation

Use the repository tool:

```bash
python tools/add_line_numbers.py --root . --output .line-numbered
```

This creates sidecar review copies under `.line-numbered/` while preserving repository paths. Sidecar output is preferred because it avoids mutating authored source documents.

## In-Place Numbering

In-place numbering is allowed only for explicit audit snapshots or sealed review exports:

```bash
python tools/add_line_numbers.py --root docs --in-place
```

Before using `--in-place`, reviewers MUST confirm that the target files are intended to become numbered artifacts rather than editable source documents.

## Exclusions

The numbering tool MUST skip generated/vendor/cache areas by default:

- `.git/`
- `.line-numbered/`
- `node_modules/`
- `.venv/`, `venv/`
- `dist/`, `build/`
- binary/media files

## Pull Request Review Requirement

Any PR that introduces new long-form documentation SHOULD either:

1. ensure the document can be processed by `tools/add_line_numbers.py`, or
2. explain why line-numbering is not appropriate.

For Sentinel review, cite exact line-numbered output when possible.

## Governance Classification

Pattern: `PAT-SENTINEL-DOC-LINE-NUMBERS-001`

Status: active after merge

Risk: low

Rationale: improves auditability without changing runtime behavior.
