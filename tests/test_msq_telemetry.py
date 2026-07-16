from tools.msq_telemetry import new_event


def test_new_event_has_required_fields():
    event = new_event(
        player_id="player-1",
        session_id="session-1",
        event_type="test_event",
        ruleset_id="ruleset-1",
        state_id="state-1",
        bin_384=0,
    )
    assert event["schema_version"] == "msq_event_v1"
    assert event["event_id"].startswith("EV-")
    assert event["player_id"] == "player-1"
    assert event["session_id"] == "session-1"
    assert event["bin_384"] == 0
