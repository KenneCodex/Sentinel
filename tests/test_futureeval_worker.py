import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import futureeval_worker as mod


class GateTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("SENTINEL_METACULUS_WRITE_APPROVED", None)
        os.environ.pop("METACULUS_TOKEN", None)

    def test_binary_payload_rejects_edges(self):
        for p in (0.0, 1.0, -0.1, 1.1):
            with self.assertRaises(ValueError):
                mod.build_binary_payload(1, p)

    def test_default_dry_run_never_posts(self):
        with tempfile.TemporaryDirectory() as td:
            receipt = Path(td) / "receipt.json"
            with patch.object(mod, "post_prediction") as post:
                rc = mod.main([
                    "--question-id",
                    "123",
                    "--probability-yes",
                    "0.42",
                    "--receipt",
                    str(receipt),
                ])
                self.assertEqual(rc, 0)
                post.assert_not_called()
                self.assertIn("DRY_RUN_NO_WRITE", receipt.read_text())

    def test_publish_requires_env_approval(self):
        os.environ["METACULUS_TOKEN"] = "not-a-real-token"
        with self.assertRaises(mod.AuthorityError):
            mod.assert_write_authority(
                publish=True,
                approval_id="HUMAN-1",
                token=os.environ["METACULUS_TOKEN"],
            )

    def test_publish_requires_approval_id(self):
        os.environ["METACULUS_TOKEN"] = "not-a-real-token"
        os.environ["SENTINEL_METACULUS_WRITE_APPROVED"] = "1"
        with self.assertRaises(mod.AuthorityError):
            mod.assert_write_authority(
                publish=True,
                approval_id=None,
                token=os.environ["METACULUS_TOKEN"],
            )

    def test_publish_requires_token(self):
        os.environ["SENTINEL_METACULUS_WRITE_APPROVED"] = "1"
        with self.assertRaises(mod.AuthorityError):
            mod.assert_write_authority(
                publish=True,
                approval_id="HUMAN-1",
                token=None,
            )

    def test_publish_authorized_only_with_all_three(self):
        os.environ["SENTINEL_METACULUS_WRITE_APPROVED"] = "1"
        mod.assert_write_authority(
            publish=True,
            approval_id="HUMAN-1",
            token="not-a-real-token",
        )


class ListingTests(unittest.TestCase):
    def test_summarize_open_questions_filters_closed(self):
        data = {"results": [
            {
                "id": 10,
                "question": {
                    "id": 100,
                    "title": "Open",
                    "type": "binary",
                    "status": "open",
                    "scheduled_close_time": "2026-09-06T00:00:00Z",
                },
            },
            {
                "id": 11,
                "question": {
                    "id": 101,
                    "title": "Closed",
                    "type": "binary",
                    "status": "closed",
                    "scheduled_close_time": "2026-09-01T00:00:00Z",
                },
            },
            {"id": 12},
        ]}
        got = mod.summarize_open_questions(data)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["question_id"], 100)

    def test_list_open_without_token_fails_closed(self):
        os.environ.pop("METACULUS_TOKEN", None)
        rc = mod.main(["--list-open"])
        self.assertEqual(rc, 2)

    def test_tournament_listing_is_get_only(self):
        fake_body = json.dumps({"results": []}).encode("utf-8")
        with patch.object(mod.urllib.request, "urlopen") as urlopen:
            response = urlopen.return_value.__enter__.return_value
            response.read.return_value = fake_body
            got = mod.list_open_tournament_questions("not-a-real-token")
            self.assertEqual(got, {"results": []})
            request = urlopen.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(
                request.headers["Authorization"],
                "Token not-a-real-token",
            )


if __name__ == "__main__":
    unittest.main()
