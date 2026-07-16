import pytest

from tools.msq_bandit_policy import DEFAULT_ARMS, arm_delta, choose_arm, init_player, update_arm


def test_arm_delta_returns_delta_for_every_default_arm():
    for arm in DEFAULT_ARMS:
        assert arm_delta(arm["arm_id"]) == arm["delta"]


def test_arm_delta_unknown_arm_raises():
    with pytest.raises(ValueError):
        arm_delta("NOT_A_REAL_ARM")


def test_choose_and_update_arm_roundtrip():
    state = init_player("player-1")
    arm = choose_arm(state, seed=1)
    update_arm(state, arm, success=True)
    assert state.runs_seen == 1
