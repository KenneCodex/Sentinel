"""Regression test for BUG-0C9A6788754B.

``.audit-logs/*.json`` only matches direct children of ``.audit-logs/``, so a
bughunt receipt written to a nested path such as ``.audit-logs/bughunt/`` was
not ignored even though the receipts are documented (``.audit-logs/README.md``,
``docs/bughunt-admission-gate.md``) as local/CI-artifact-only and never meant
to be committed. The pattern must also keep ignoring the top-level
``.audit-logs/priority-config.json`` template, which the same rule already
carved out with a negation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _is_ignored(relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", relative_path],
        cwd=REPO_ROOT,
        check=False,
    )
    return result.returncode == 0


def test_nested_audit_log_json_is_ignored():
    assert _is_ignored(".audit-logs/bughunt/RUN-BUGHUNT-20260827-example.json")


def test_top_level_audit_log_json_is_ignored():
    assert _is_ignored(".audit-logs/some-run.json")


def test_priority_config_template_is_not_ignored():
    assert not _is_ignored(".audit-logs/priority-config.json")
