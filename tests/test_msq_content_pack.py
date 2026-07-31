"""Validation for the shipped MSQ content pack.

The pack and its schema are authored artifacts that no runtime module loads, so
nothing previously detected drift between them — or between the pack and the
defaults that ``tools/msq_demo_run.py`` hardcodes.
"""

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK_PATH = ROOT / "data" / "msq" / "content_pack_v1.json"
SCHEMA_PATH = ROOT / "schemas" / "msq_content_pack_v1.schema.json"


@pytest.fixture(scope="module")
def pack():
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_content_pack_matches_schema(pack, schema):
    jsonschema.validate(pack, schema)


def test_ruleset_rng_profile_references_resolve(pack):
    declared = {profile["rng_profile_id"] for profile in pack["rng_profiles"]}

    for ruleset in pack["rulesets"]:
        referenced = ruleset["spawn_rules"]["rng_profile_id"]
        assert referenced in declared, (
            f"ruleset {ruleset['ruleset_id']} references undeclared "
            f"rng_profile_id {referenced!r}"
        )


def test_declared_guardrails_match_policy_defaults(pack):
    """The pack is the source of truth; DEFAULT_GUARDRAILS must not drift from it."""
    from dataclasses import asdict

    from tools.msq_bandit_policy import DEFAULT_GUARDRAILS

    assert pack["ai_tuning"]["guardrails"] == asdict(DEFAULT_GUARDRAILS)


def test_load_guardrails_reads_the_shipped_pack(pack):
    from tools.msq_bandit_policy import load_guardrails

    guardrails = load_guardrails(PACK_PATH)
    declared = pack["ai_tuning"]["guardrails"]

    assert guardrails.min_runs_before_personalization == declared["min_runs_before_personalization"]
    assert (
        guardrails.max_difficulty_step_per_session
        == declared["max_difficulty_step_per_session"]
    )


def test_load_guardrails_falls_back_when_pack_is_missing(tmp_path):
    from tools.msq_bandit_policy import DEFAULT_GUARDRAILS, load_guardrails

    assert load_guardrails(tmp_path / "absent.json") == DEFAULT_GUARDRAILS


def test_every_arm_knob_has_a_declared_bound():
    """bounded_changes_only is only meaningful if every shipped knob is bounded."""
    from tools.msq_bandit_policy import DEFAULT_ARMS, SCALE_KNOB_BOUNDS, STEP_KNOBS

    for arm in DEFAULT_ARMS:
        for knob in arm["delta"]:
            assert knob in STEP_KNOBS or knob in SCALE_KNOB_BOUNDS, (
                f"arm {arm['arm_id']} uses knob {knob!r} with no declared bound"
            )


def test_demo_defaults_match_shipped_ruleset(pack):
    """The demo runner hardcodes a ruleset id and target sum; keep them in sync."""
    from tools.msq_demo_run import build_parser

    defaults = vars(build_parser().parse_args([]))
    rulesets = {ruleset["ruleset_id"]: ruleset for ruleset in pack["rulesets"]}

    assert defaults["ruleset_id"] in rulesets, (
        f"demo default ruleset {defaults['ruleset_id']!r} is not in the content pack"
    )
    assert defaults["target_sum"] == rulesets[defaults["ruleset_id"]]["target_sum"]
