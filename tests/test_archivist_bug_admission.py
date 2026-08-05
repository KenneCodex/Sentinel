from tools.archivist_bug_admission import (
    SurfaceReviewed,
    build_receipt,
    fingerprint_candidate,
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
