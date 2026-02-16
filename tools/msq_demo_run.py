from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.msq_bandit_policy import (
    arm_delta,
    choose_arm,
    load_or_init_player_state,
    save_player_state,
    update_arm,
)
from tools.msq_state import MSQState, state_id_and_bin
from tools.msq_telemetry import append_jsonl, new_event


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--player-id", default="P-DEMO")
    p.add_argument("--ruleset-id", default="RS-MSQ-0001")
    p.add_argument("--target-sum", type=int, default=15)
    p.add_argument("--policy-path", default="audit/msq/policy/player_P-DEMO.json")
    p.add_argument("--events", default="audit/msq/events.jsonl")
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--success", action="store_true", help="Mark session as success to update bandit")
    args = p.parse_args()

    session_id = f"S-{uuid.uuid4().hex[:12].upper()}"

    # A dummy starting state (Lo Shu solved) for demo only.
    tiles = [8, 1, 6, 3, 5, 7, 4, 9, 2]
    locks = [False] * 9
    st = MSQState(
        size=3,
        target_sum=args.target_sum,
        ruleset_id=args.ruleset_id,
        tiles=tiles,
        locks=locks,
    )
    sid, b = state_id_and_bin(st)

    policy_path = Path(args.policy_path)
    events_path = Path(args.events)

    pol = load_or_init_player_state(policy_path, args.player_id)
    arm = choose_arm(pol, seed=args.seed)
    delta = arm_delta(arm)

    append_jsonl(
        events_path,
        new_event(
            args.player_id,
            session_id,
            "session_start",
            args.ruleset_id,
            sid,
            b,
            metrics={"arm": arm, "delta": delta},
        ),
    )
    append_jsonl(
        events_path,
        new_event(
            args.player_id,
            session_id,
            "session_end",
            args.ruleset_id,
            sid,
            b,
            metrics={"success": bool(args.success)},
        ),
    )

    update_arm(pol, arm, success=bool(args.success))
    save_player_state(policy_path, pol)

    print(
        json.dumps(
            {
                "player_id": args.player_id,
                "session_id": session_id,
                "chosen_arm": arm,
                "delta": delta,
                "state_id": sid,
                "bin_384": b,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
