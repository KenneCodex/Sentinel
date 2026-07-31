import json

import pytest

from tools.msq_bandit_policy import (
    BASELINE_ARM_ID,
    DEFAULT_ARMS,
    DEFAULT_GUARDRAILS,
    SCALE_KNOB_BOUNDS,
    STEP_KNOBS,
    Guardrails,
    arm_delta,
    bound_delta,
    choose_arm,
    init_player,
    update_arm,
)

NO_WARMUP = Guardrails(min_runs_before_personalization=0)

DEFAULT_ARMS_BY_ID = {arm["arm_id"]: arm for arm in DEFAULT_ARMS}


def _warm(state):
    """Advance a player past the personalization warmup."""
    state.runs_seen = DEFAULT_GUARDRAILS.min_runs_before_personalization
    return state


def test_arm_delta_returns_bounded_delta_for_every_default_arm():
    limit = DEFAULT_GUARDRAILS.max_difficulty_step_per_session

    for arm in DEFAULT_ARMS:
        delta = arm_delta(arm["arm_id"])
        assert set(delta) == set(arm["delta"])

        for knob, value in delta.items():
            if knob in STEP_KNOBS:
                assert abs(value) <= limit
            else:
                low, high = SCALE_KNOB_BOUNDS[knob]
                assert low <= value <= high


def test_arm_delta_unknown_arm_raises():
    with pytest.raises(ValueError):
        arm_delta("NOT_A_REAL_ARM")


def test_choose_and_update_arm_roundtrip():
    state = _warm(init_player("player-1"))
    arm = choose_arm(state, seed=1)
    update_arm(state, arm, success=True)
    assert state.runs_seen == DEFAULT_GUARDRAILS.min_runs_before_personalization + 1
    updated_arm = next(a for a in state.arms if a.arm_id == arm)
    assert updated_arm.alpha == 2.0
    assert updated_arm.beta == 1.0


# --- max_difficulty_step_per_session ---------------------------------------


def test_step_knob_exceeding_limit_is_clamped():
    """C_MORE_HINTS authors hint_after_fails=2, above the declared limit of 1."""
    assert DEFAULT_ARMS_BY_ID["C_MORE_HINTS"]["delta"]["hint_after_fails"] == 2
    assert arm_delta("C_MORE_HINTS") == {"hint_after_fails": 1}


def test_step_knob_clamp_follows_the_declared_limit():
    relaxed = Guardrails(max_difficulty_step_per_session=3)
    assert bound_delta({"max_locks": 5}, relaxed) == {"max_locks": 3}
    assert bound_delta({"max_locks": 2}, relaxed) == {"max_locks": 2}


def test_step_knob_clamp_bounds_negative_steps():
    assert bound_delta({"spawn_count_per_tick": -4}) == {"spawn_count_per_tick": -1}


def test_scale_knob_is_clamped_to_its_multiplier_range():
    low, high = SCALE_KNOB_BOUNDS["base_SE_mult"]
    assert bound_delta({"base_SE_mult": 99.0}) == {"base_SE_mult": high}
    assert bound_delta({"base_SE_mult": 0.0}) == {"base_SE_mult": low}


def test_undeclared_knob_is_refused_under_bounded_changes_only():
    with pytest.raises(ValueError, match="no declared bound"):
        bound_delta({"unbounded_knob": 10_000})


def test_undeclared_knob_passes_through_when_bounding_is_disabled():
    unbounded = Guardrails(bounded_changes_only=False)
    assert bound_delta({"unbounded_knob": 7}, unbounded) == {"unbounded_knob": 7}


# --- min_runs_before_personalization ----------------------------------------


def test_baseline_arm_is_forced_during_warmup():
    state = init_player("player-1")

    for _ in range(DEFAULT_GUARDRAILS.min_runs_before_personalization):
        # Seed varies the Thompson draw; the guardrail must win regardless.
        assert choose_arm(state, seed=state.runs_seen) == BASELINE_ARM_ID
        update_arm(state, BASELINE_ARM_ID, success=True)


def test_personalization_begins_once_warmup_is_satisfied():
    state = init_player("player-1")
    state.runs_seen = DEFAULT_GUARDRAILS.min_runs_before_personalization

    # Make a non-baseline arm overwhelmingly likely to win the sample.
    for arm in state.arms:
        if arm.arm_id == "D_MORE_LOCKS":
            arm.alpha, arm.beta = 500.0, 1.0
        else:
            arm.alpha, arm.beta = 1.0, 500.0

    assert choose_arm(state, seed=7) == "D_MORE_LOCKS"


def test_warmup_of_zero_permits_immediate_personalization():
    state = init_player("player-1")
    for arm in state.arms:
        if arm.arm_id == "E_IDLE_BOOST":
            arm.alpha, arm.beta = 500.0, 1.0
        else:
            arm.alpha, arm.beta = 1.0, 500.0

    assert state.runs_seen == 0
    assert choose_arm(state, seed=7, guardrails=NO_WARMUP) == "E_IDLE_BOOST"


# --- guardrail value validation ---------------------------------------------
#
# The content pack is plain JSON that nothing validates at runtime, so a
# declared value must be checked before it is allowed to bind.


@pytest.mark.parametrize(
    "declared",
    [
        {"max_difficulty_step_per_session": 9999},  # would defeat the clamp
        {"max_difficulty_step_per_session": -1},
        {"max_difficulty_step_per_session": None},
        {"max_difficulty_step_per_session": True},  # bool is not a step count
        {"max_difficulty_step_per_session": "1"},
        {"min_runs_before_personalization": "3"},  # would TypeError in choose_arm
        {"min_runs_before_personalization": -5},  # would disable the warmup
        {"min_runs_before_personalization": 21},
        {"bounded_changes_only": "yes"},
    ],
)
def test_invalid_guardrail_value_falls_back_to_default(tmp_path, declared):
    from tools.msq_bandit_policy import load_guardrails

    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps({"ai_tuning": {"guardrails": declared}}), encoding="utf-8")

    guardrails = load_guardrails(pack)
    for name in declared:
        assert getattr(guardrails, name) == getattr(DEFAULT_GUARDRAILS, name)


def test_out_of_range_step_limit_cannot_defeat_the_clamp(tmp_path):
    pack = tmp_path / "pack.json"
    pack.write_text(
        json.dumps({"ai_tuning": {"guardrails": {"max_difficulty_step_per_session": 9999}}}),
        encoding="utf-8",
    )

    from tools.msq_bandit_policy import load_guardrails

    assert arm_delta("C_MORE_HINTS", load_guardrails(pack)) == {"hint_after_fails": 1}


def test_valid_in_range_guardrail_still_binds(tmp_path):
    from tools.msq_bandit_policy import load_guardrails

    pack = tmp_path / "pack.json"
    pack.write_text(
        json.dumps({"ai_tuning": {"guardrails": {"max_difficulty_step_per_session": 3}}}),
        encoding="utf-8",
    )

    guardrails = load_guardrails(pack)
    assert guardrails.max_difficulty_step_per_session == 3
    assert arm_delta("C_MORE_HINTS", guardrails) == {"hint_after_fails": 2}


# --- persisted-state reconciliation -----------------------------------------


def test_state_missing_the_baseline_arm_is_reconciled(tmp_path):
    """choose_arm can return the baseline arm during warmup, so it must exist."""
    from tools.msq_bandit_policy import (
        load_or_init_player_state,
        save_player_state,
    )

    path = tmp_path / "player.json"
    path.write_text(
        json.dumps(
            {
                "player_id": "P1",
                "runs_seen": 0,
                "arms": [{"arm_id": "D_MORE_LOCKS", "alpha": 4.0, "beta": 2.0}],
            }
        ),
        encoding="utf-8",
    )

    state = load_or_init_player_state(path, "P1")

    assert {a.arm_id for a in state.arms} == {a["arm_id"] for a in DEFAULT_ARMS}

    # Learned parameters for the surviving arm are preserved, not reset.
    locks = next(a for a in state.arms if a.arm_id == "D_MORE_LOCKS")
    assert (locks.alpha, locks.beta) == (4.0, 2.0)

    # The full warmup round-trip no longer raises Unknown arm_id.
    arm = choose_arm(state)
    assert arm == BASELINE_ARM_ID
    update_arm(state, arm, success=True)
    save_player_state(path, state)


def test_unknown_persisted_arm_is_dropped(tmp_path):
    from tools.msq_bandit_policy import load_or_init_player_state

    path = tmp_path / "player.json"
    path.write_text(
        json.dumps(
            {
                "player_id": "P1",
                "runs_seen": 0,
                "arms": [{"arm_id": "Z_RETIRED_ARM", "alpha": 9.0, "beta": 9.0}],
            }
        ),
        encoding="utf-8",
    )

    state = load_or_init_player_state(path, "P1")
    assert "Z_RETIRED_ARM" not in {a.arm_id for a in state.arms}
