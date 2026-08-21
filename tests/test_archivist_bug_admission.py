import json
import sys
from unittest.mock import patch

import pytest

from tools.archivist_bug_admission import (
    InputLoadError,
    SurfaceReviewed,
    _load_json,
    _open_pr_entries,
    _registry_entries,
    build_receipt,
    fingerprint_candidate,
    normalize_candidate,
)

REPOSITORY = "KenneCodex/Sentinel"
BASE_SHA = "e3a0ab3022348590e68350ae0d8a856535a23c9f"
CANDIDATE = {
    "component": "cli-validation.sh",
    "failure_class": "premature_exit",
    "trigger": "required command missing under set -e",
    "affected_symbol": "validate_required_tools",
    "normalized_root_cause": "unguarded nonzero function return",
}


def _write_candidate_mode_inputs(tmp_path, *, candidate=CANDIDATE, open_prs=None, registry=None):
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps({"entries": []} if registry is None else registry), encoding="utf-8")
    open_prs_path = tmp_path / "open-prs.json"
    open_prs_path.write_text(json.dumps([] if open_prs is None else open_prs), encoding="utf-8")
    return candidate_path, registry_path, open_prs_path


def _run_main(tmp_path, *argv):
    from tools.archivist_bug_admission import main

    output_path = tmp_path / "receipt.json"
    args = [
        "--run-id", "run-test",
        "--repository", REPOSITORY,
        "--base-sha", BASE_SHA,
        *argv,
        "--output", str(output_path),
    ]
    with patch.object(sys, "argv", ["archivist_bug_admission.py", *args]):
        exit_code = main()
    return exit_code, json.loads(output_path.read_text(encoding="utf-8"))


def test_fingerprint_is_stable_across_cosmetic_variation():
    defect_id, fingerprint, normalized = fingerprint_candidate(REPOSITORY, CANDIDATE)
    cosmetic = dict(CANDIDATE)
    cosmetic["component"] = ".\\CLI-VALIDATION.SH"
    cosmetic["affected_symbol"] = "`validate_required_tools`"
    cosmetic["failure_class"] = " PREMATURE_EXIT "
    cosmetic_id, cosmetic_fingerprint, cosmetic_normalized = fingerprint_candidate(
        "kennecodex/sentinel", cosmetic
    )

    assert cosmetic_id == defect_id
    assert cosmetic_fingerprint == fingerprint
    assert cosmetic_normalized == normalized


def test_semantic_punctuation_change_remains_distinct():
    defect_id, fingerprint, _ = fingerprint_candidate(REPOSITORY, CANDIDATE)
    altered = dict(CANDIDATE)
    altered["trigger"] = "required command missing under set-e"
    altered_id, altered_fingerprint, _ = fingerprint_candidate(REPOSITORY, altered)

    assert altered_id != defect_id
    assert altered_fingerprint != fingerprint


def test_base_sha_does_not_change_defect_identity():
    first = build_receipt(
        run_id="run-1",
        repository=REPOSITORY,
        base_sha=BASE_SHA,
        candidate=CANDIDATE,
        timestamp="2026-08-05T00:00:00+00:00",
    )
    second = build_receipt(
        run_id="run-2",
        repository=REPOSITORY,
        base_sha="another-base-sha",
        candidate=CANDIDATE,
        timestamp="2026-08-05T01:00:00+00:00",
    )
    assert first["defect"]["defect_id"] == second["defect"]["defect_id"]
    assert first["defect"]["fingerprint"] == second["defect"]["fingerprint"]


def test_registry_match_suppresses_duplicate_pr():
    defect_id, _, _ = fingerprint_candidate(REPOSITORY, CANDIDATE)
    registry = [
        {
            "defect_id": defect_id,
            "canonical_pr": 31,
            "duplicate_prs": [32, 33],
            "status": "candidate",
        }
    ]
    receipt = build_receipt(
        run_id="run-duplicate",
        repository=REPOSITORY,
        base_sha=BASE_SHA,
        candidate=CANDIDATE,
        registry=registry,
        surface=SurfaceReviewed(files=24, tests=40, reproductions_attempted=1),
        timestamp="2026-08-05T00:00:00+00:00",
    )

    assert receipt["result"] == "DUPLICATE"
    assert receipt["pr_allowed"] is False
    assert receipt["pr_created"] is False
    assert receipt["duplicate_of"]["canonical_pr"] == 31
    assert receipt["duplicate_of"]["related_prs"] == [32, 33]


def test_open_pr_marker_suppresses_duplicate_without_registry():
    defect_id, fingerprint, _ = fingerprint_candidate(REPOSITORY, CANDIDATE)
    open_prs = [
        {
            "number": 44,
            "title": "fix: candidate",
            "body": f"Archivist-Defect-ID: {defect_id}\nArchivist-Fingerprint: {fingerprint}",
        }
    ]
    receipt = build_receipt(
        run_id="run-open-pr",
        repository=REPOSITORY,
        base_sha=BASE_SHA,
        candidate=CANDIDATE,
        open_prs=open_prs,
        timestamp="2026-08-05T00:00:00+00:00",
    )

    assert receipt["result"] == "DUPLICATE"
    assert receipt["duplicate_of"]["source"] == "open-pr-marker"
    assert receipt["duplicate_of"]["canonical_pr"] == 44


def test_new_candidate_is_admitted_and_produces_pr_markers():
    receipt = build_receipt(
        run_id="run-new",
        repository=REPOSITORY,
        base_sha=BASE_SHA,
        candidate=CANDIDATE,
        timestamp="2026-08-05T00:00:00+00:00",
    )

    assert receipt["result"] == "NEW"
    assert receipt["pr_allowed"] is True
    assert receipt["pr_created"] is False
    assert receipt["pr_markers"]["defect_id"].startswith("Archivist-Defect-ID: BUG-")
    assert receipt["pr_markers"]["fingerprint"].startswith("Archivist-Fingerprint: ")


def test_no_candidate_produces_durable_clean_receipt():
    receipt = build_receipt(
        run_id="run-clean",
        repository=REPOSITORY,
        base_sha=BASE_SHA,
        surface=SurfaceReviewed(files=24, tests=40, reproductions_attempted=3),
        timestamp="2026-08-05T00:00:00+00:00",
    )

    assert receipt["result"] == "CLEAN"
    assert receipt["unique_reproducible_defects"] == 0
    assert receipt["pr_allowed"] is False
    assert receipt["surface_reviewed"] == {
        "files": 24,
        "tests": 40,
        "reproductions_attempted": 3,
    }


def test_recognised_open_pr_wrappers_are_unwrapped():
    entry = {"number": 44, "title": "fix: candidate"}
    assert _open_pr_entries([entry]) == [entry]
    for key in ("pull_requests", "items", "results"):
        assert _open_pr_entries({key: [entry]}) == [entry]


@pytest.mark.parametrize(
    "payload",
    [
        {"open_pull_requests": [{"number": 44}]},
        {"data": {"repository": {"pullRequests": {"nodes": []}}}},
        {},
        "not-json-data",
        42,
        [{"number": 44}, "not-an-object"],
    ],
)
def test_unreadable_open_pr_payload_is_rejected_rather_than_read_as_empty(payload):
    with pytest.raises(ValueError):
        _open_pr_entries(payload)


def test_registry_rejects_non_object_entries():
    with pytest.raises(ValueError):
        _registry_entries({"entries": [{"defect_id": "BUG-X"}, "bad-entry"]})


def test_load_json_wraps_malformed_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(InputLoadError):
        _load_json(path, {})


def test_whitespace_only_candidate_fields_are_rejected_as_missing():
    whitespace_candidate = {
        "component": "   ",
        "failure_class": "   ",
        "trigger": "   ",
        "affected_symbol": "   ",
        "normalized_root_cause": "   ",
    }
    with pytest.raises(ValueError):
        normalize_candidate(REPOSITORY, whitespace_candidate)


def test_unusable_open_pr_evidence_blocks_instead_of_admitting_new(tmp_path, capsys):
    candidate_path, registry_path, open_prs_path = _write_candidate_mode_inputs(
        tmp_path,
        open_prs={"open_pull_requests": [{"number": 44}]},
    )
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(candidate_path),
        "--registry", str(registry_path),
        "--open-prs", str(open_prs_path),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False


def test_missing_open_pr_file_blocks_when_explicitly_requested(tmp_path, capsys):
    candidate_path, registry_path, _ = _write_candidate_mode_inputs(tmp_path)
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(candidate_path),
        "--registry", str(registry_path),
        "--open-prs", str(tmp_path / "never-written.json"),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False


def test_omitted_open_pr_file_blocks_candidate_mode(tmp_path, capsys):
    candidate_path, registry_path, _ = _write_candidate_mode_inputs(tmp_path)
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(candidate_path),
        "--registry", str(registry_path),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False
    assert "requires --open-prs" in receipt["next_action"]


def test_missing_candidate_file_blocks_instead_of_emitting_clean(tmp_path, capsys):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text('{"entries": []}', encoding="utf-8")
    open_prs_path = tmp_path / "open-prs.json"
    open_prs_path.write_text("[]", encoding="utf-8")
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(tmp_path / "missing-candidate.json"),
        "--registry", str(registry_path),
        "--open-prs", str(open_prs_path),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False


def test_missing_registry_blocks_candidate_mode(tmp_path, capsys):
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(CANDIDATE), encoding="utf-8")
    open_prs_path = tmp_path / "open-prs.json"
    open_prs_path.write_text("[]", encoding="utf-8")
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(candidate_path),
        "--registry", str(tmp_path / "missing-registry.json"),
        "--open-prs", str(open_prs_path),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False


def test_malformed_registry_still_writes_blocked_receipt(tmp_path, capsys):
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(CANDIDATE), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    registry_path.write_text("{not valid json", encoding="utf-8")
    open_prs_path = tmp_path / "open-prs.json"
    open_prs_path.write_text("[]", encoding="utf-8")
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(candidate_path),
        "--registry", str(registry_path),
        "--open-prs", str(open_prs_path),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False


def test_whitespace_candidate_still_writes_blocked_receipt(tmp_path, capsys):
    candidate = dict(CANDIDATE)
    candidate["trigger"] = "   "
    candidate_path, registry_path, open_prs_path = _write_candidate_mode_inputs(
        tmp_path,
        candidate=candidate,
    )
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(candidate_path),
        "--registry", str(registry_path),
        "--open-prs", str(open_prs_path),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False


def test_valid_candidate_mode_with_empty_lineage_can_still_admit_new(tmp_path, capsys):
    candidate_path, registry_path, open_prs_path = _write_candidate_mode_inputs(tmp_path)
    exit_code, receipt = _run_main(
        tmp_path,
        "--candidate", str(candidate_path),
        "--registry", str(registry_path),
        "--open-prs", str(open_prs_path),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "NEW"
    assert receipt["pr_allowed"] is True


def test_explicit_blocked_reason_writes_receipt_without_reading_bad_optional_inputs(tmp_path, capsys):
    bad_candidate = tmp_path / "candidate.json"
    bad_candidate.write_text("{not valid json", encoding="utf-8")
    exit_code, receipt = _run_main(
        tmp_path,
        "--blocked-reason", "validation unavailable",
        "--candidate", str(bad_candidate),
    )
    capsys.readouterr()
    assert exit_code == 0
    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False


def test_blocked_reason_takes_precedence_over_candidate():
    receipt = build_receipt(
        run_id="run-blocked",
        repository=REPOSITORY,
        base_sha=BASE_SHA,
        candidate=CANDIDATE,
        blocked_reason="Repository source unavailable",
        timestamp="2026-08-05T00:00:00+00:00",
    )

    assert receipt["result"] == "BLOCKED"
    assert receipt["pr_allowed"] is False
    assert receipt["unique_reproducible_defects"] is None
    assert "Repository source unavailable" in receipt["notification"]["message"]
