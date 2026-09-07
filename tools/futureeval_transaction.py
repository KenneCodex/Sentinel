#!/usr/bin/env python3
"""Plan MiniBench forecast+reasoning transactions and classify partial outcomes.

This module intentionally contains NO network transport and reads NO credentials.
It prepares the exact Metaculus forecast/comment payloads, binds them to a validated
precommit envelope, and records deterministic transaction-state receipts.

External writes remain disabled in this slice. Synthetic step results can be passed
to ``classify_external_results`` by tests or a future transport layer so that a later
network implementation cannot collapse partial external reality into a generic error.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.futureeval_envelope import canonical_sha256, validate_envelope
from tools.futureeval_worker import build_binary_payload

SCHEMA = "sentinel.metaculus.transaction-receipt/0.1"
COMMENT_ENDPOINT = "/api/comments/create/"
FORECAST_ENDPOINT = "/api/questions/forecast/"


class TransactionError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedTransaction:
    envelope_sha256: str
    authority_id: str
    forecast_ordinal: int
    question_id: int
    post_id: int
    forecast_payload: list[dict[str, Any]]
    comment_payload: dict[str, Any]
    forecast_payload_sha256: str
    comment_payload_sha256: str


@dataclass(frozen=True)
class StepResult:
    attempted: bool
    ok: bool | None
    status_code: int | None = None
    response_sha256: str | None = None
    error_type: str | None = None


@dataclass(frozen=True)
class TransactionReceipt:
    schema: str
    ts_utc: str
    state: str
    envelope_sha256: str
    authority_id: str
    forecast_ordinal: int
    question_id: int
    post_id: int
    forecast_endpoint: str
    comment_endpoint: str
    forecast_payload_sha256: str
    comment_payload_sha256: str
    forecast_step: dict[str, Any]
    comment_step: dict[str, Any]
    retry_scope: str
    external_write_enabled: bool
    network_access_performed: bool
    credential_access_performed: bool


def build_comment_payload(post_id: int, reasoning_text: str) -> dict[str, Any]:
    text = reasoning_text.strip()
    if not text:
        raise TransactionError("reasoning_text must be non-empty")
    return {
        "text": text,
        "parent": None,
        "included_forecast": True,
        "is_private": True,
        "on_post": int(post_id),
    }


def prepare_transaction(
    *,
    envelope: dict[str, Any],
    forecast_ordinal: int,
    question_id: int,
    post_id: int,
    probability_yes: float,
    reasoning_text: str,
    now: datetime | None = None,
) -> PreparedTransaction:
    validated = validate_envelope(envelope, now=now)
    if not isinstance(forecast_ordinal, int) or isinstance(forecast_ordinal, bool):
        raise TransactionError("forecast_ordinal must be an integer")
    if not 1 <= forecast_ordinal <= validated["max_forecasts"]:
        raise TransactionError("forecast_ordinal exceeds the precommitted max_forecasts")
    if question_id <= 0 or post_id <= 0:
        raise TransactionError("question_id and post_id must be positive")

    forecast_payload = build_binary_payload(question_id, probability_yes)
    comment_payload = build_comment_payload(post_id, reasoning_text)
    return PreparedTransaction(
        envelope_sha256=validated["envelope_sha256"],
        authority_id=validated["authority_id"],
        forecast_ordinal=forecast_ordinal,
        question_id=int(question_id),
        post_id=int(post_id),
        forecast_payload=forecast_payload,
        comment_payload=comment_payload,
        forecast_payload_sha256=canonical_sha256(forecast_payload),
        comment_payload_sha256=canonical_sha256(comment_payload),
    )


def dry_run_receipt(prepared: PreparedTransaction) -> TransactionReceipt:
    not_attempted = asdict(StepResult(attempted=False, ok=None))
    return TransactionReceipt(
        schema=SCHEMA,
        ts_utc=datetime.now(timezone.utc).isoformat(),
        state="DRY_RUN_NO_WRITE",
        envelope_sha256=prepared.envelope_sha256,
        authority_id=prepared.authority_id,
        forecast_ordinal=prepared.forecast_ordinal,
        question_id=prepared.question_id,
        post_id=prepared.post_id,
        forecast_endpoint=FORECAST_ENDPOINT,
        comment_endpoint=COMMENT_ENDPOINT,
        forecast_payload_sha256=prepared.forecast_payload_sha256,
        comment_payload_sha256=prepared.comment_payload_sha256,
        forecast_step=not_attempted,
        comment_step=not_attempted,
        retry_scope="none",
        external_write_enabled=False,
        network_access_performed=False,
        credential_access_performed=False,
    )


def classify_external_results(
    prepared: PreparedTransaction,
    *,
    forecast: StepResult,
    comment: StepResult,
) -> TransactionReceipt:
    """Classify observed step results without performing any I/O."""
    if not forecast.attempted:
        if comment.attempted:
            raise TransactionError("comment cannot be attempted before forecast")
        state = "NO_EXTERNAL_WRITE_ATTEMPTED"
        retry_scope = "full_transaction"
    elif forecast.ok is not True:
        if comment.attempted:
            raise TransactionError("comment must not be attempted after forecast failure")
        state = "FORECAST_FAILED_NO_COMMENT_ATTEMPT"
        retry_scope = "full_transaction"
    else:
        if not comment.attempted:
            state = "FORECAST_ONLY_PARTIAL_WRITE"
            retry_scope = "comment_only"
        elif comment.ok is True:
            state = "COMPLETE_EXTERNAL_WRITE"
            retry_scope = "none"
        else:
            state = "FORECAST_ONLY_PARTIAL_WRITE"
            retry_scope = "comment_only"

    return TransactionReceipt(
        schema=SCHEMA,
        ts_utc=datetime.now(timezone.utc).isoformat(),
        state=state,
        envelope_sha256=prepared.envelope_sha256,
        authority_id=prepared.authority_id,
        forecast_ordinal=prepared.forecast_ordinal,
        question_id=prepared.question_id,
        post_id=prepared.post_id,
        forecast_endpoint=FORECAST_ENDPOINT,
        comment_endpoint=COMMENT_ENDPOINT,
        forecast_payload_sha256=prepared.forecast_payload_sha256,
        comment_payload_sha256=prepared.comment_payload_sha256,
        forecast_step=asdict(forecast),
        comment_step=asdict(comment),
        retry_scope=retry_scope,
        external_write_enabled=False,
        network_access_performed=False,
        credential_access_performed=False,
    )


def write_receipt(path: Path, receipt: TransactionReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(receipt), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a no-network MiniBench forecast+comment transaction")
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--forecast-ordinal", type=int, required=True)
    parser.add_argument("--question-id", type=int, required=True)
    parser.add_argument("--post-id", type=int, required=True)
    parser.add_argument("--probability-yes", type=float, required=True)
    parser.add_argument("--reasoning", required=True)
    parser.add_argument("--receipt", type=Path, default=Path("receipts/minibench-transaction.json"))
    args = parser.parse_args(argv)

    try:
        envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
        if not isinstance(envelope, dict):
            raise TransactionError("envelope root must be a JSON object")
        prepared = prepare_transaction(
            envelope=envelope,
            forecast_ordinal=args.forecast_ordinal,
            question_id=args.question_id,
            post_id=args.post_id,
            probability_yes=args.probability_yes,
            reasoning_text=args.reasoning,
        )
        receipt = dry_run_receipt(prepared)
        write_receipt(args.receipt, receipt)
        print(json.dumps({
            "state": receipt.state,
            "envelope_sha256": prepared.envelope_sha256,
            "forecast_payload": prepared.forecast_payload,
            "comment_payload": prepared.comment_payload,
            "forecast_payload_sha256": prepared.forecast_payload_sha256,
            "comment_payload_sha256": prepared.comment_payload_sha256,
            "receipt": str(args.receipt),
        }, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        blocked = {
            "schema": SCHEMA,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "state": "BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
            "external_write_enabled": False,
            "network_access_performed": False,
            "credential_access_performed": False,
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(blocked, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(blocked, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
