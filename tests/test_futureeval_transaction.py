import unittest
from datetime import datetime, timezone

from tools import futureeval_transaction as mod


class TransactionTests(unittest.TestCase):
    def valid_envelope(self):
        return {
            "schema": "sentinel.metaculus.autonomy-envelope/0.1",
            "competition_slug": "minibench",
            "tournament_ref": "minibench",
            "authority_id": "HUMAN-PRECOMMIT-TEST-1",
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

    def prepared(self):
        return mod.prepare_transaction(
            envelope=self.valid_envelope(),
            forecast_ordinal=1,
            question_id=123,
            post_id=456,
            probability_yes=0.42,
            reasoning_text="Evidence supports a calibrated 42% estimate.",
            now=datetime(2026, 9, 7, 12, tzinfo=timezone.utc),
        )

    def test_comment_payload_matches_private_included_forecast_shape(self):
        got = mod.build_comment_payload(456, "Reasoning")
        self.assertEqual(got, {
            "text": "Reasoning",
            "parent": None,
            "included_forecast": True,
            "is_private": True,
            "on_post": 456,
        })

    def test_empty_reasoning_fails_closed(self):
        with self.assertRaises(mod.TransactionError):
            mod.build_comment_payload(456, "   ")

    def test_prepare_binds_envelope_and_both_payload_hashes(self):
        got = self.prepared()
        self.assertEqual(got.forecast_payload[0]["question"], 123)
        self.assertEqual(got.comment_payload["on_post"], 456)
        self.assertTrue(got.forecast_payload_sha256)
        self.assertTrue(got.comment_payload_sha256)
        self.assertTrue(got.envelope_sha256)

    def test_forecast_ordinal_must_stay_inside_precommit_cap(self):
        with self.assertRaises(mod.TransactionError):
            mod.prepare_transaction(
                envelope=self.valid_envelope(),
                forecast_ordinal=61,
                question_id=123,
                post_id=456,
                probability_yes=0.42,
                reasoning_text="Reasoning",
                now=datetime(2026, 9, 7, 12, tzinfo=timezone.utc),
            )

    def test_dry_run_receipt_proves_no_external_access(self):
        receipt = mod.dry_run_receipt(self.prepared())
        self.assertEqual(receipt.state, "DRY_RUN_NO_WRITE")
        self.assertFalse(receipt.external_write_enabled)
        self.assertFalse(receipt.network_access_performed)
        self.assertFalse(receipt.credential_access_performed)
        self.assertFalse(receipt.forecast_step["attempted"])
        self.assertFalse(receipt.comment_step["attempted"])

    def test_complete_external_result_is_distinct_state(self):
        receipt = mod.classify_external_results(
            self.prepared(),
            forecast=mod.StepResult(True, True, 201, "forecast-response"),
            comment=mod.StepResult(True, True, 201, "comment-response"),
        )
        self.assertEqual(receipt.state, "COMPLETE_EXTERNAL_WRITE")
        self.assertEqual(receipt.retry_scope, "none")

    def test_forecast_success_comment_failure_is_partial_write(self):
        receipt = mod.classify_external_results(
            self.prepared(),
            forecast=mod.StepResult(True, True, 201, "forecast-response"),
            comment=mod.StepResult(True, False, 500, None, "HTTPError"),
        )
        self.assertEqual(receipt.state, "FORECAST_ONLY_PARTIAL_WRITE")
        self.assertEqual(receipt.retry_scope, "comment_only")

    def test_forecast_success_comment_not_attempted_is_partial_write(self):
        receipt = mod.classify_external_results(
            self.prepared(),
            forecast=mod.StepResult(True, True, 201, "forecast-response"),
            comment=mod.StepResult(False, None),
        )
        self.assertEqual(receipt.state, "FORECAST_ONLY_PARTIAL_WRITE")
        self.assertEqual(receipt.retry_scope, "comment_only")

    def test_forecast_failure_prohibits_comment_attempt(self):
        receipt = mod.classify_external_results(
            self.prepared(),
            forecast=mod.StepResult(True, False, 500, None, "HTTPError"),
            comment=mod.StepResult(False, None),
        )
        self.assertEqual(receipt.state, "FORECAST_FAILED_NO_COMMENT_ATTEMPT")
        self.assertEqual(receipt.retry_scope, "full_transaction")

    def test_comment_attempt_after_forecast_failure_is_rejected(self):
        with self.assertRaises(mod.TransactionError):
            mod.classify_external_results(
                self.prepared(),
                forecast=mod.StepResult(True, False, 500, None, "HTTPError"),
                comment=mod.StepResult(True, True, 201, "impossible"),
            )

    def test_comment_attempt_before_forecast_is_rejected(self):
        with self.assertRaises(mod.TransactionError):
            mod.classify_external_results(
                self.prepared(),
                forecast=mod.StepResult(False, None),
                comment=mod.StepResult(True, True, 201, "impossible"),
            )


if __name__ == "__main__":
    unittest.main()
