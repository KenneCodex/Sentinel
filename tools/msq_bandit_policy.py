from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, fields, replace
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


@dataclass(frozen=True)
class Guardrails:
    """Bounds declared by ``ai_tuning.guardrails`` in the MSQ content pack.

    Defaults mirror the shipped pack. ``tests/test_msq_content_pack.py`` asserts
    that they stay in step, so editing the pack without editing these fails the
    build rather than silently loosening a bound.
    """

    max_difficulty_step_per_session: int = 1
    min_runs_before_personalization: int = 3
    no_sensitive_inference: bool = True
    bounded_changes_only: bool = True


DEFAULT_GUARDRAILS = Guardrails()

# Accepted range for each integer guardrail, mirroring the bounds in
# schemas/msq_content_pack_v1.schema.json. A test asserts the two stay in step.
# Fields not listed here are booleans and are type-checked only.
_GUARDRAIL_INT_RANGES = {
    "max_difficulty_step_per_session": (0, 3),
    "min_runs_before_personalization": (0, 20),
}

_GUARDRAIL_FIELDS = {f.name for f in fields(Guardrails)}


def _is_valid_guardrail(name: str, value: Any) -> bool:
    """Whether a declared guardrail value is well-typed and within schema range."""
    if name in _GUARDRAIL_INT_RANGES:
        # bool is a subclass of int; a boolean is not a valid step count.
        if not isinstance(value, int) or isinstance(value, bool):
            return False
        low, high = _GUARDRAIL_INT_RANGES[name]
        return low <= value <= high
    return isinstance(value, bool)

CONTENT_PACK_PATH = Path(__file__).resolve().parents[1] / "data" / "msq" / "content_pack_v1.json"

BASELINE_ARM_ID = "A_BASELINE"

DEFAULT_ARMS = [
    # Minimal knob deltas; clients can interpret these into config tweaks.
    {"arm_id": BASELINE_ARM_ID, "delta": {}},
    {"arm_id": "B_MORE_SPAWNS", "delta": {"spawn_count_per_tick": +1}},
    {"arm_id": "C_MORE_HINTS", "delta": {"hint_after_fails": 2}},
    {"arm_id": "D_MORE_LOCKS", "delta": {"max_locks": +1}},
    {"arm_id": "E_IDLE_BOOST", "delta": {"base_SE_mult": 1.1, "base_CE_mult": 1.05}},
]

DEFAULT_ARMS_MAP = {a["arm_id"]: a for a in DEFAULT_ARMS}

# Knob taxonomy for guardrail enforcement.
#
# "Step" knobs move a difficulty setting by a whole number of steps, so
# max_difficulty_step_per_session bounds them directly. "Scale" knobs are
# multiplicative rate adjustments, where a step count has no meaning; they carry
# explicit multiplier ranges instead. A knob in neither table has no declared
# bound, so bounded_changes_only forbids applying it.
STEP_KNOBS = frozenset({"spawn_count_per_tick", "max_locks", "hint_after_fails"})

SCALE_KNOB_BOUNDS = {
    "base_SE_mult": (0.9, 1.25),
    "base_CE_mult": (0.9, 1.25),
}


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


def load_guardrails(pack_path: Path = CONTENT_PACK_PATH) -> Guardrails:
    """Read ``ai_tuning.guardrails`` from a content pack.

    Falls back to :data:`DEFAULT_GUARDRAILS` when the pack is absent or does not
    declare guardrails. Unrecognised keys are ignored rather than rejected, so a
    newer pack does not break an older client.

    A recognised key binds only if its value is well-typed and inside the range
    the schema declares; otherwise that single field falls back to its default.
    The pack is plain JSON that nothing validates at runtime, so without this an
    out-of-range bound would simply be obeyed — a pack declaring
    ``max_difficulty_step_per_session: 9999`` would turn the clamp into a no-op,
    and a string where an integer belongs would fail inside ``choose_arm``.
    Falling back to the shipped default is the fail-safe direction.
    """
    obj = _load_json(pack_path)
    if not isinstance(obj, dict):
        return DEFAULT_GUARDRAILS

    ai_tuning = obj.get("ai_tuning")
    if not isinstance(ai_tuning, dict):
        return DEFAULT_GUARDRAILS

    declared = ai_tuning.get("guardrails")
    if not isinstance(declared, dict):
        return DEFAULT_GUARDRAILS

    accepted = {
        name: value
        for name, value in declared.items()
        if name in _GUARDRAIL_FIELDS and _is_valid_guardrail(name, value)
    }
    return replace(DEFAULT_GUARDRAILS, **accepted)


def choose_arm(
    state: PlayerPolicyState,
    seed: Optional[int] = None,
    guardrails: Guardrails = DEFAULT_GUARDRAILS,
) -> str:
    """Select an arm for this session, subject to the personalization guardrail.

    ``min_runs_before_personalization`` requires a warmup: until the player has
    that many recorded runs, every session gets the baseline arm and no
    personalization occurs. Sampling begins only once the warmup is satisfied.
    """
    if state.runs_seen < guardrails.min_runs_before_personalization:
        return BASELINE_ARM_ID

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


def bound_delta(delta: Dict[str, Any], guardrails: Guardrails = DEFAULT_GUARDRAILS) -> Dict[str, Any]:
    """Clamp a knob delta to the bounds the guardrails declare.

    ``max_difficulty_step_per_session`` caps the magnitude of every step knob.
    Scale knobs are clamped to their declared multiplier range instead, since a
    step count does not describe a multiplier.

    A knob in neither table has no declared bound. ``bounded_changes_only``
    means such a knob cannot be applied, so this raises rather than passing an
    unbounded value through to the client — adding an arm therefore requires
    declaring how its knobs are bounded.
    """
    limit = guardrails.max_difficulty_step_per_session
    bounded: Dict[str, Any] = {}

    for knob, value in delta.items():
        if knob in STEP_KNOBS:
            bounded[knob] = max(-limit, min(limit, value))
        elif knob in SCALE_KNOB_BOUNDS:
            low, high = SCALE_KNOB_BOUNDS[knob]
            bounded[knob] = max(low, min(high, value))
        elif guardrails.bounded_changes_only:
            raise ValueError(
                f"Knob {knob!r} has no declared bound; add it to STEP_KNOBS or "
                f"SCALE_KNOB_BOUNDS before using it in an arm delta"
            )
        else:
            bounded[knob] = value

    return bounded


def arm_delta(arm_id: str, guardrails: Guardrails = DEFAULT_GUARDRAILS) -> Dict[str, Any]:
    """Return the guardrail-bounded delta for an arm.

    The returned delta is always bounded; callers cannot obtain the raw table
    entry through this function. ``DEFAULT_ARMS`` remains available for tests
    and tooling that need to inspect the unbounded authoring values.
    """
    arm = DEFAULT_ARMS_MAP.get(arm_id)
    if arm is None:
        raise ValueError(f"Unknown arm_id: {arm_id}")
    return bound_delta(arm["delta"], guardrails)


def _reconcile_arms(loaded: List[ArmState]) -> List[ArmState]:
    """Align persisted arms with the current arm table.

    Learned Beta parameters are kept for arms that still exist, arms that no
    longer exist are dropped, and arms absent from the file get fresh priors.

    This matters because ``choose_arm`` returns :data:`BASELINE_ARM_ID` during
    the personalization warmup rather than sampling from ``state.arms``. A state
    file written against a different arm table could omit that arm, and the
    caller would then hand an arm_id to ``update_arm`` that the state does not
    contain, raising ``Unknown arm_id``. Reconciling on load guarantees every
    arm in ``DEFAULT_ARMS`` is present.
    """
    by_id = {arm.arm_id: arm for arm in loaded}
    return [by_id.get(spec["arm_id"], ArmState(spec["arm_id"])) for spec in DEFAULT_ARMS]


def load_or_init_player_state(path: Path, player_id: str) -> PlayerPolicyState:
    obj = _load_json(path)
    if not obj:
        return init_player(player_id)

    # Validate loaded structure and ensure it belongs to the requested player.
    if not isinstance(obj, dict):
        return init_player(player_id)

    loaded_player_id = obj.get("player_id")
    runs_seen = obj.get("runs_seen")
    arms_raw = obj.get("arms")

    # If the persisted player_id doesn't match, or types are wrong, start fresh.
    if not isinstance(loaded_player_id, str) or loaded_player_id != player_id:
        return init_player(player_id)
    if not isinstance(runs_seen, int):
        return init_player(player_id)
    if not isinstance(arms_raw, list):
        return init_player(player_id)

    arms: List[ArmState] = []
    for a in arms_raw:
        if not isinstance(a, dict):
            return init_player(player_id)
        try:
            arms.append(ArmState(**a))
        except (TypeError, KeyError):
            return init_player(player_id)

    # Reject stale/incomplete arm sets (e.g. a retired arm_id, or an empty
    # list) so callers never crash later in choose_arm/arm_delta.
    if not arms or {arm.arm_id for arm in arms} != set(DEFAULT_ARMS_MAP):
        return init_player(player_id)

    # Use the function argument player_id, which we've validated against disk.
    return PlayerPolicyState(
        player_id=player_id, runs_seen=runs_seen, arms=_reconcile_arms(arms)
    )


def save_player_state(path: Path, state: PlayerPolicyState) -> None:
    _save_json(path, asdict(state))
