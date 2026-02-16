from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    ensure_parent_dir(path)
    # Use a lock file to prevent concurrent write issues.
    lock_path = path.with_suffix(path.suffix + ".lock")
    from filelock import FileLock
    with FileLock(lock_path):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


@dataclass
class MSQEvent:
    schema_version: str
    event_id: str
    created_at: str
    player_id: str
    session_id: str
    event_type: str
    ruleset_id: str
    state_id: str
    bin_384: int
    move: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


def new_event(
    player_id: str,
    session_id: str,
    event_type: str,
    ruleset_id: str,
    state_id: str,
    bin_384: int,
    move: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ev = MSQEvent(
        schema_version="msq_event_v1",
        event_id=f"EV-{uuid.uuid4().hex[:16].upper()}",
        created_at=utc_now_iso(),
        player_id=player_id,
        session_id=session_id,
        event_type=event_type,
        ruleset_id=ruleset_id,
        state_id=state_id,
        bin_384=bin_384,
        move=move,
        metrics=metrics,
    )
    return asdict(ev)


def _self_test() -> None:
    """
    Lightweight self-test to detect schema drift and JSONL append regressions.

    This function is intended to be run via:

        python -m tools.msq_telemetry

    or:

        python tools/msq_telemetry.py
    """
    # Validate event shape and field formats.
    event = new_event(
        player_id="player-1",
        session_id="session-1",
        event_type="test_event",
        ruleset_id="ruleset-1",
        state_id="state-1",
        bin_384=0,
    )

    required_fields = {
        "schema_version",
        "event_id",
        "created_at",
        "player_id",
        "session_id",
        "event_type",
        "ruleset_id",
        "state_id",
        "bin_384",
    }
    missing = required_fields.difference(event.keys())
    assert not missing, f"MSQEvent missing required fields: {missing}"

    # Check stable schema/version and ID prefixes.
    assert isinstance(event["schema_version"], str), "schema_version must be a string"
    assert event["schema_version"].startswith(
        "msq_event_v"
    ), f"Unexpected schema_version prefix: {event['schema_version']!r}"

    assert isinstance(event["event_id"], str), "event_id must be a string"
    assert event["event_id"].startswith(
        "EV-"
    ), f"Unexpected event_id prefix: {event['event_id']!r}"
    assert len(event["event_id"]) > 3, "event_id appears too short"

    # Validate ISO-8601 datetime format.
    try:
        datetime.fromisoformat(event["created_at"])
    except Exception as exc:  # pragma: no cover - defensive
        raise AssertionError(
            f"created_at is not a valid ISO-8601 datetime: {event['created_at']!r}"
        ) from exc

    # Validate JSONL append behavior.
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "events.jsonl"
        append_jsonl(tmp_path, event)

        contents = tmp_path.read_text(encoding="utf-8").splitlines()
        assert len(contents) == 1, f"Expected 1 JSONL line, found {len(contents)}"

        loaded = json.loads(contents[0])
        assert (
            loaded == event
        ), "Round-tripped JSONL record does not match original event"


if __name__ == "__main__":  # pragma: no cover - optional runtime self-check
    _self_test()
