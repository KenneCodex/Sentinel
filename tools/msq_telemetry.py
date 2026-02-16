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
