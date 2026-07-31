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


def test_demo_defaults_match_shipped_ruleset(pack):
    """The demo runner hardcodes a ruleset id and target sum; keep them in sync."""
    from tools.msq_demo_run import build_parser

    defaults = vars(build_parser().parse_args([]))
    rulesets = {ruleset["ruleset_id"]: ruleset for ruleset in pack["rulesets"]}

    assert defaults["ruleset_id"] in rulesets, (
        f"demo default ruleset {defaults['ruleset_id']!r} is not in the content pack"
    )
    assert defaults["target_sum"] == rulesets[defaults["ruleset_id"]]["target_sum"]
