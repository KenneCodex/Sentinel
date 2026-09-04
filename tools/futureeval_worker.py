#!/usr/bin/env python3
"""SentinelAI local-first FutureEval worker.

Default posture: READ/PREPARE only. Network writes are impossible unless all of:
  * --publish is passed
  * SENTINEL_METACULUS_WRITE_APPROVED=1
  * a non-empty --approval-id is supplied
  * METACULUS_TOKEN is present

No credential is written to disk by this program.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://www.metaculus.com/api"
SUMMER_2026_TOURNAMENT_ID = 33022


class AuthorityError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthorityReceipt:
    ts_utc: str
    mode: str
    approval_id: str | None
    question_id: int
    payload_sha256: str
    publish_requested: bool
    publish_authorized: bool
    outcome: str


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_binary_payload(question_id: int, probability_yes: float) -> list[dict[str, Any]]:
    if not 0.0 < probability_yes < 1.0:
        raise ValueError("probability_yes must be strictly between 0 and 1")
    return [{
        "question": int(question_id),
        "source": "api",
        "probability_yes": float(probability_yes),
        "probability_yes_per_category": None,
        "continuous_cdf": None,
    }]


def assert_write_authority(*, publish: bool, approval_id: str | None, token: str | None) -> None:
    if not publish:
        return
    if os.getenv("SENTINEL_METACULUS_WRITE_APPROVED") != "1":
        raise AuthorityError("publish blocked: SENTINEL_METACULUS_WRITE_APPROVED is not 1")
    if not approval_id or not approval_id.strip():
        raise AuthorityError("publish blocked: --approval-id is required")
    if not token:
        raise AuthorityError("publish blocked: METACULUS_TOKEN is not present")


def list_open_tournament_questions(
    token: str,
    tournament_id: int | str = SUMMER_2026_TOURNAMENT_ID,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Read open tournament posts. This performs an authenticated GET only."""
    from urllib.parse import urlencode

    params = [
        ("limit", str(limit)),
        ("offset", str(offset)),
        ("order_by", "-hotness"),
        ("forecast_type", "binary,multiple_choice,numeric,discrete"),
        ("tournaments", str(tournament_id)),
        ("statuses", "open"),
        ("include_description", "true"),
    ]
    request = urllib.request.Request(
        f"{API_BASE}/posts/?{urlencode(params)}",
        headers={
            "Authorization": f"Token {token}",
            "User-Agent": "SentinelAI-DOS80211b0t/0.1",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: fixed HTTPS origin
        return json.loads(response.read().decode("utf-8"))


def summarize_open_questions(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for post in data.get("results", []):
        q = post.get("question")
        if not isinstance(q, dict) or q.get("status") != "open":
            continue
        out.append({
            "post_id": post.get("id"),
            "question_id": q.get("id"),
            "title": q.get("title"),
            "type": q.get("type"),
            "scheduled_close_time": q.get("scheduled_close_time"),
        })
    return out


def post_prediction(payload: list[dict[str, Any]], token: str) -> tuple[int, str]:
    request = urllib.request.Request(
        f"{API_BASE}/questions/forecast/",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": "SentinelAI-DOS80211b0t/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: fixed HTTPS origin
        return response.status, response.read().decode("utf-8", errors="replace")


def write_receipt(path: Path, receipt: AuthorityReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(receipt), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-first SentinelAI FutureEval forecast gate")
    parser.add_argument(
        "--list-open",
        action="store_true",
        help="authenticated read-only listing of open Summer 2026 tournament questions",
    )
    parser.add_argument("--question-id", type=int)
    parser.add_argument("--probability-yes", type=float)
    parser.add_argument("--publish", action="store_true", help="request a real Metaculus write")
    parser.add_argument("--approval-id", default=None, help="human review/approval receipt identifier")
    parser.add_argument("--receipt", type=Path, default=Path("receipts/latest.json"))
    args = parser.parse_args(argv)

    token = os.getenv("METACULUS_TOKEN")
    if args.list_open:
        if not token:
            print("read blocked: METACULUS_TOKEN is not present", file=sys.stderr)
            return 2
        data = list_open_tournament_questions(token)
        print(json.dumps({
            "tournament_id": SUMMER_2026_TOURNAMENT_ID,
            "open_questions": summarize_open_questions(data),
        }, indent=2))
        return 0

    if args.question_id is None or args.probability_yes is None:
        parser.error("--question-id and --probability-yes are required unless --list-open is used")

    payload = build_binary_payload(args.question_id, args.probability_yes)
    payload_hash = canonical_sha256(payload)

    try:
        assert_write_authority(publish=args.publish, approval_id=args.approval_id, token=token)
        if args.publish:
            status, body = post_prediction(payload, token=token or "")
            outcome = f"POSTED HTTP {status}"
            print(body)
        else:
            outcome = "DRY_RUN_NO_WRITE"
            print(json.dumps({"mode": "dry-run", "payload": payload, "payload_sha256": payload_hash}, indent=2))
        authorized = bool(args.publish)
    except Exception as exc:
        outcome = f"BLOCKED: {type(exc).__name__}: {exc}"
        authorized = False
        receipt = AuthorityReceipt(
            ts_utc=datetime.now(timezone.utc).isoformat(),
            mode="publish" if args.publish else "dry-run",
            approval_id=args.approval_id,
            question_id=args.question_id,
            payload_sha256=payload_hash,
            publish_requested=args.publish,
            publish_authorized=authorized,
            outcome=outcome,
        )
        write_receipt(args.receipt, receipt)
        print(outcome, file=sys.stderr)
        return 2

    receipt = AuthorityReceipt(
        ts_utc=datetime.now(timezone.utc).isoformat(),
        mode="publish" if args.publish else "dry-run",
        approval_id=args.approval_id,
        question_id=args.question_id,
        payload_sha256=payload_hash,
        publish_requested=args.publish,
        publish_authorized=authorized,
        outcome=outcome,
    )
    write_receipt(args.receipt, receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
