import json
from pathlib import Path

from tools.msq_telemetry import new_event

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "msq_event_v1.schema.json"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_matches_schema(event, schema):
    for field in schema["required"]:
        assert field in event, f"missing required field: {field}"

    assert event["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert event["event_type"] in schema["properties"]["event_type"]["enum"]

    bin_schema = schema["properties"]["bin_384"]
    assert bin_schema["minimum"] <= event["bin_384"] <= bin_schema["maximum"]

    if not schema.get("additionalProperties", True):
        assert set(event.keys()) <= set(schema["properties"].keys())


def test_new_event_has_required_fields():
    event = new_event(
        player_id="player-1",
        session_id="session-1",
        event_type="session_start",
        ruleset_id="ruleset-1",
        state_id="state-1",
        bin_384=0,
    )
    assert event["schema_version"] == "msq_event_v1"
    assert event["event_id"].startswith("EV-")
    assert event["player_id"] == "player-1"
    assert event["session_id"] == "session-1"
    assert event["bin_384"] == 0


def test_new_event_matches_schema():
    schema = _load_schema()
    event = new_event(
        player_id="player-1",
        session_id="session-1",
        event_type="session_start",
        ruleset_id="ruleset-1",
        state_id="state-1",
        bin_384=0,
    )
    _assert_matches_schema(event, schema)
