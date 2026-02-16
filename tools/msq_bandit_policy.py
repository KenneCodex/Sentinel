from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Bounded, per-player Thompson sampling over a small set of "arms".
# This only SELECTS an arm; it does not auto-apply global patches.


@dataclass
class ArmState:
    arm_id: str
    alpha: float = 1.0  # Beta prior
    beta: float = 1.0


@dataclass
class PlayerPolicyState:
    player_id: str
    runs_seen: int
    arms: List[ArmState]


DEFAULT_ARMS = [
    # Minimal knob deltas; clients can interpret these into config tweaks.
    {"arm_id": "A_BASELINE", "delta": {}},
    {"arm_id": "B_MORE_SPAWNS", "delta": {"spawn_count_per_tick": +1}},
    {"arm_id": "C_MORE_HINTS", "delta": {"hint_after_fails": 2}},
    {"arm_id": "D_MORE_LOCKS", "delta": {"max_locks": +1}},
    {"arm_id": "E_IDLE_BOOST", "delta": {"base_SE_mult": 1.1, "base_CE_mult": 1.05}},
]


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _save_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def init_player(player_id: str) -> PlayerPolicyState:
    arms = [ArmState(a["arm_id"]) for a in DEFAULT_ARMS]
    return PlayerPolicyState(player_id=player_id, runs_seen=0, arms=arms)


def choose_arm(state: PlayerPolicyState, seed: Optional[int] = None) -> str:
    rng = random.Random(seed)
    best_arm = None
    best_sample = -1.0
    for arm in state.arms:
        # Thompson sample from Beta(alpha, beta)
        sample = rng.betavariate(arm.alpha, arm.beta)
        if sample > best_sample:
            best_sample = sample
            best_arm = arm.arm_id
    assert best_arm is not None
    return best_arm


def update_arm(state: PlayerPolicyState, arm_id: str, success: bool) -> None:
    for arm in state.arms:
        if arm.arm_id == arm_id:
            if success:
                arm.alpha += 1.0
            else:
                arm.beta += 1.0
            state.runs_seen += 1
            return
    raise ValueError(f"Unknown arm_id: {arm_id}")


def arm_delta(arm_id: str) -> Dict[str, Any]:
    for a in DEFAULT_ARMS:
        if a["arm_id"] == arm_id:
            return a["delta"]
    raise ValueError(f"Unknown arm_id: {arm_id}")


def load_or_init_player_state(path: Path, player_id: str) -> PlayerPolicyState:
    obj = _load_json(path)
    if not obj:
        return init_player(player_id)

    arms = [ArmState(**a) for a in obj["arms"]]
    return PlayerPolicyState(player_id=obj["player_id"], runs_seen=obj["runs_seen"], arms=arms)


def save_player_state(path: Path, state: PlayerPolicyState) -> None:
    _save_json(path, asdict(state))
