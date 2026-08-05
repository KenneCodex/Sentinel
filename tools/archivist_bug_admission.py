#!/usr/bin/env python3
"""Archivist admission gate for scheduled bug-finder runs.

The gate separates a *run* from a *defect*. It assigns a stable defect identity,
checks known defect lineage and open pull-request markers, then emits one durable
receipt state: CLEAN, NEW, DUPLICATE, or BLOCKED.

The tool deliberately does not open or modify pull requests. A NEW result grants
permission for the calling routine to prepare one; every other result suppresses
that action and preserves a receipt instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "bughunt_receipt_v1"
RESULTS = {"CLEAN", "NEW", "DUPLICATE", "BLOCKED"}
REQUIRED_CANDIDATE_FIELDS = (
    "component",
    "failure_class",
    "trigger",
    "affected_symbol",
    "normalized_root_cause",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("`", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_component(value: Any) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw:
        return ""
    normalized = str(PurePosixPath(raw))
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lower()


def normalize_candidate(repository: str, candidate: Mapping[str, Any]) -> dict[str, str]:
    missing = [field for field in REQUIRED_CANDIDATE_FIELDS if not candidate.get(field)]
    if missing:
        raise ValueError(f"candidate is missing required fields: {', '.join(missing)}")

    return {
        "repository": _normalize_text(repository),
        "component": _normalize_component(candidate["component"]),
        "failure_class": _normalize_text(candidate["failure_class"]),
        "trigger": _normalize_text(candidate["trigger"]),
        "affected_symbol": _normalize_text(candidate["affected_symbol"]),
        "normalized_root_cause": _normalize_text(candidate["normalized_root_cause"]),
    }


def fingerprint_candidate(repository: str, candidate: Mapping[str, Any]) -> tuple[str, str, dict[str, str]]:
    normalized = normalize_candidate(repository, candidate)
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"BUG-{digest[:12].upper()}", digest, normalized


def _load_json(path: str | Path | None, default: Any) -> Any:
    if not path:
        return default
    target = Path(path)
    if not target.exists():
        return default
    return json.loads(target.read_text(encoding="utf-8"))


def _registry_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        entries = payload.get("entries", [])
    else:
        entries = payload
    if not isinstance(entries, list):
        raise ValueError("registry entries must be a list")
    return [entry for entry in entries if isinstance(entry, dict)]


def _open_pr_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("pull_requests", "items", "results"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def _marker_matches(pr: Mapping[str, Any], defect_id: str, fingerprint: str) -> bool:
    marker_text = "\n".join(
        [
            str(pr.get("title") or ""),
            str(pr.get("body") or ""),
            str(pr.get("archivist_defect_id") or ""),
            str(pr.get("archivist_fingerprint") or ""),
        ]
    ).lower()
    return defect_id.lower() in marker_text or fingerprint.lower() in marker_text


def find_duplicate(
    defect_id: str,
    fingerprint: str,
    normalized: Mapping[str, str],
    registry: Sequence[Mapping[str, Any]],
    open_prs: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    for entry in registry:
        if str(entry.get("defect_id") or "").upper() == defect_id:
            return {
                "source": "registry",
                "defect_id": defect_id,
                "canonical_pr": entry.get("canonical_pr"),
                "related_prs": sorted(set(entry.get("duplicate_prs", []) or [])),
                "status": entry.get("status", "known"),
            }

        comparable = {
            key: _normalize_component(entry.get(key)) if key == "component" else _normalize_text(entry.get(key))
            for key in REQUIRED_CANDIDATE_FIELDS
        }
        if all(comparable[key] == normalized[key] for key in REQUIRED_CANDIDATE_FIELDS):
            return {
                "source": "registry-fields",
                "defect_id": str(entry.get("defect_id") or defect_id),
                "canonical_pr": entry.get("canonical_pr"),
                "related_prs": sorted(set(entry.get("duplicate_prs", []) or [])),
                "status": entry.get("status", "known"),
            }

    for pr in open_prs:
        if _marker_matches(pr, defect_id, fingerprint):
            number = pr.get("number") or pr.get("pr_number")
            return {
                "source": "open-pr-marker",
                "defect_id": defect_id,
                "canonical_pr": number,
                "related_prs": [number] if number is not None else [],
                "status": "open",
            }
    return None


@dataclass(frozen=True)
class SurfaceReviewed:
    files: int = 0
    tests: int = 0
    reproductions_attempted: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "files": max(0, int(self.files)),
            "tests": max(0, int(self.tests)),
            "reproductions_attempted": max(0, int(self.reproductions_attempted)),
        }


def build_receipt(
    *,
    run_id: str,
    repository: str,
    base_sha: str,
    candidate: Mapping[str, Any] | None = None,
    registry: Sequence[Mapping[str, Any]] = (),
    open_prs: Sequence[Mapping[str, Any]] = (),
    blocked_reason: str | None = None,
    surface: SurfaceReviewed | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not run_id.strip():
        raise ValueError("run_id is required")
    if not repository.strip():
        raise ValueError("repository is required")
    if not base_sha.strip():
        raise ValueError("base_sha is required")

    reviewed = (surface or SurfaceReviewed()).as_dict()
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id.strip(),
        "repository": repository.strip(),
        "base_sha": base_sha.strip(),
        "timestamp": timestamp or now_iso(),
        "surface_reviewed": reviewed,
        "files_changed": [],
        "pr_created": False,
    }

    if blocked_reason:
        receipt.update(
            {
                "result": "BLOCKED",
                "unique_reproducible_defects": None,
                "pr_allowed": False,
                "next_action": blocked_reason.strip(),
                "notification": {"message": f"Bug-hunt blocked: {blocked_reason.strip()}"},
            }
        )
        return receipt

    if candidate is None:
        receipt.update(
            {
                "result": "CLEAN",
                "unique_reproducible_defects": 0,
                "pr_allowed": False,
                "next_action": "Preserve the clean-run receipt; no pull request is required.",
                "notification": {
                    "message": "Bug-hunt completed; no unique reproducible defects were identified."
                },
            }
        )
        return receipt

    defect_id, fingerprint, normalized = fingerprint_candidate(repository, candidate)
    defect_payload: dict[str, Any] = {
        "defect_id": defect_id,
        "fingerprint": fingerprint,
        **normalized,
    }
    if candidate.get("evidence") is not None:
        defect_payload["evidence"] = candidate["evidence"]
    receipt["defect"] = defect_payload

    duplicate = find_duplicate(defect_id, fingerprint, normalized, registry, open_prs)
    if duplicate:
        receipt.update(
            {
                "result": "DUPLICATE",
                "unique_reproducible_defects": 0,
                "duplicate_of": duplicate,
                "pr_allowed": False,
                "next_action": "Attach any unique evidence to the canonical lineage; do not open a competing pull request.",
                "notification": {
                    "message": "Known defect reproduced; no duplicate pull request was created."
                },
            }
        )
    else:
        receipt.update(
            {
                "result": "NEW",
                "unique_reproducible_defects": 1,
                "pr_allowed": True,
                "next_action": "Prepare the smallest verified patch and include the Archivist defect markers in the draft pull request.",
                "notification": {
                    "message": f"New reproducible defect {defect_id} admitted for a draft pull request."
                },
                "pr_markers": {
                    "defect_id": f"Archivist-Defect-ID: {defect_id}",
                    "fingerprint": f"Archivist-Fingerprint: {fingerprint}",
                },
            }
        )

    if receipt["result"] not in RESULTS:
        raise AssertionError("unexpected receipt result")
    return receipt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--candidate", help="Path to candidate JSON. Omit for a CLEAN receipt.")
    parser.add_argument("--registry", default="data/bughunt/defect_registry_v1.json")
    parser.add_argument("--open-prs", help="Optional JSON file containing open pull-request metadata.")
    parser.add_argument("--blocked-reason")
    parser.add_argument("--files-reviewed", type=int, default=0)
    parser.add_argument("--tests-executed", type=int, default=0)
    parser.add_argument("--reproductions-attempted", type=int, default=0)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    candidate = _load_json(args.candidate, None)
    registry = _registry_entries(_load_json(args.registry, {"entries": []}))
    open_prs = _open_pr_entries(_load_json(args.open_prs, []))
    surface = SurfaceReviewed(
        files=args.files_reviewed,
        tests=args.tests_executed,
        reproductions_attempted=args.reproductions_attempted,
    )
    receipt = build_receipt(
        run_id=args.run_id,
        repository=args.repository,
        base_sha=args.base_sha,
        candidate=candidate,
        registry=registry,
        open_prs=open_prs,
        blocked_reason=args.blocked_reason,
        surface=surface,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
