#!/usr/bin/env python3
"""Validate a precommitted Metaculus MiniBench autonomy envelope.

This module performs NO network access and does not read credentials. It exists to
prove that any future autonomous forecasting run is bounded before active-question
outputs are generated or inspected by a human.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "sentinel.metaculus.autonomy-envelope/0.1"
MINIBENCH_REF = "minibench"
ALLOWED_WRITE_METHODS = ["comment", "forecast"]
ALLOWED_NETWORK_HOSTS = ["www.metaculus.com"]
PLACEHOLDER_AUTHORITY_IDS = {"", "REPLACE_BEFORE_ACTIVATION", "PLACEHOLDER"}


class EnvelopeError(ValueError):
    pass


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise EnvelopeError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EnvelopeError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_envelope(envelope: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    if envelope.get("schema") != SCHEMA:
        raise EnvelopeError(f"schema must equal {SCHEMA}")
    if envelope.get("competition_slug") != "minibench":
        raise EnvelopeError("competition_slug must be minibench")
    if envelope.get("tournament_ref") != MINIBENCH_REF:
        raise EnvelopeError("tournament_ref must be minibench")

    authority_id = str(envelope.get("authority_id", "")).strip()
    if authority_id in PLACEHOLDER_AUTHORITY_IDS:
        raise EnvelopeError("authority_id must be a non-placeholder precommit identifier")

    valid_from = parse_utc(str(envelope.get("valid_from_utc", "")), "valid_from_utc")
    expires = parse_utc(str(envelope.get("expires_utc", "")), "expires_utc")
    if not valid_from < expires:
        raise EnvelopeError("valid_from_utc must be before expires_utc")

    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if observed < valid_from:
        raise EnvelopeError("envelope is not active yet")
    if observed >= expires:
        raise EnvelopeError("envelope is expired")

    max_forecasts = envelope.get("max_forecasts")
    if not isinstance(max_forecasts, int) or isinstance(max_forecasts, bool):
        raise EnvelopeError("max_forecasts must be an integer")
    if not 1 <= max_forecasts <= 100:
        raise EnvelopeError("max_forecasts must be between 1 and 100")

    if envelope.get("require_reasoning_comment") is not True:
        raise EnvelopeError("require_reasoning_comment must be true")
    if envelope.get("human_in_loop_during_forecasting") is not False:
        raise EnvelopeError("human_in_loop_during_forecasting must be false")
    if envelope.get("allow_live_tuning") is not False:
        raise EnvelopeError("allow_live_tuning must be false")
    if envelope.get("allow_forecast_preview_to_human") is not False:
        raise EnvelopeError("allow_forecast_preview_to_human must be false")

    write_methods = sorted(envelope.get("allowed_write_methods", []))
    if write_methods != ALLOWED_WRITE_METHODS:
        raise EnvelopeError("allowed_write_methods must be exactly comment and forecast")

    network_hosts = sorted(envelope.get("allowed_network_hosts", []))
    if network_hosts != ALLOWED_NETWORK_HOSTS:
        raise EnvelopeError("allowed_network_hosts must be exactly www.metaculus.com")

    return {
        "status": "VALID_PRECOMMIT_ENVELOPE",
        "schema": SCHEMA,
        "competition_slug": "minibench",
        "tournament_ref": MINIBENCH_REF,
        "authority_id": authority_id,
        "valid_from_utc": valid_from.isoformat(),
        "expires_utc": expires.isoformat(),
        "max_forecasts": max_forecasts,
        "envelope_sha256": canonical_sha256(envelope),
        "network_access_performed": False,
        "credential_access_performed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a no-network MiniBench autonomy envelope")
    parser.add_argument("envelope", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)

    try:
        envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
        if not isinstance(envelope, dict):
            raise EnvelopeError("envelope root must be a JSON object")
        result = validate_envelope(envelope)
    except Exception as exc:
        result = {
            "status": "BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
            "network_access_performed": False,
            "credential_access_performed": False,
        }
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
