import unittest
from datetime import datetime, timezone

from tools import futureeval_envelope as mod


NOW = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)


def valid_envelope():
    return {
        "schema": mod.SCHEMA,
        "competition_slug": "minibench",
        "tournament_ref": "minibench",
        "authority_id": "HUMAN-PRECOMMIT-2026-09-07-A",
        "valid_from_utc": "2026-09-07T00:00:00Z",
        "expires_utc": "2026-09-25T23:59:59Z",
        "max_forecasts": 60,
        "require_reasoning_comment": True,
        "human_in_loop_during_forecasting": False,
        "allow_live_tuning": False,
        "allow_forecast_preview_to_human": False,
        "allowed_write_methods": ["forecast", "comment"],
        "allowed_network_hosts": ["www.metaculus.com"],
    }


class EnvelopeTests(unittest.TestCase):
    def test_valid_precommit_envelope(self):
        result = mod.validate_envelope(valid_envelope(), now=NOW)
        self.assertEqual(result["status"], "VALID_PRECOMMIT_ENVELOPE")
        self.assertEqual(result["max_forecasts"], 60)
        self.assertFalse(result["network_access_performed"])
        self.assertFalse(result["credential_access_performed"])
        self.assertEqual(len(result["envelope_sha256"]), 64)

    def test_placeholder_authority_is_blocked(self):
        envelope = valid_envelope()
        envelope["authority_id"] = "REPLACE_BEFORE_ACTIVATION"
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)

    def test_human_preview_is_blocked(self):
        envelope = valid_envelope()
        envelope["allow_forecast_preview_to_human"] = True
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)

    def test_live_tuning_is_blocked(self):
        envelope = valid_envelope()
        envelope["allow_live_tuning"] = True
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)

    def test_reasoning_comment_is_mandatory(self):
        envelope = valid_envelope()
        envelope["require_reasoning_comment"] = False
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)

    def test_extra_network_host_is_blocked(self):
        envelope = valid_envelope()
        envelope["allowed_network_hosts"].append("example.com")
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)

    def test_extra_write_method_is_blocked(self):
        envelope = valid_envelope()
        envelope["allowed_write_methods"].append("account_update")
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)

    def test_expired_envelope_is_blocked(self):
        envelope = valid_envelope()
        envelope["expires_utc"] = "2026-09-07T19:59:59Z"
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)

    def test_forecast_cap_is_bounded(self):
        envelope = valid_envelope()
        envelope["max_forecasts"] = 101
        with self.assertRaises(mod.EnvelopeError):
            mod.validate_envelope(envelope, now=NOW)


if __name__ == "__main__":
    unittest.main()
