import json
import os
import tempfile
import unittest
from unittest.mock import patch

import ig_fetch_comments as scanner


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class ScannerTests(unittest.TestCase):
    def test_current_graph_version_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(scanner._graph_root(), "https://graph.facebook.com/v26.0")

    def test_token_is_sent_in_header_not_url(self):
        captured = {}

        def open_request(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["timeout"] = timeout
            return FakeResponse({"data": []})

        with patch.object(scanner.urllib.request, "urlopen", open_request):
            self.assertEqual(
                scanner._request_json(
                    "https://graph.facebook.com/v26.0/items?access_token=leaked&after=cursor",
                    "dummy-token",
                ),
                {"data": []},
            )
        self.assertNotIn("dummy-token", captured["url"])
        self.assertNotIn("access_token", captured["url"])
        self.assertIn("after=cursor", captured["url"])
        self.assertEqual(captured["authorization"], "Bearer dummy-token")
        self.assertEqual(captured["timeout"], 60)

    def test_refuses_pagination_to_untrusted_host(self):
        with self.assertRaises(ValueError):
            scanner._request_json("https://example.test/steal", "dummy-token")

    def test_fetch_expands_replies_from_reply_edge(self):
        media = [{"id": "m1", "comments_count": 1, "permalink": "https://example.test/post"}]
        comments = [{"id": "c1", "text": "Parent", "username": "parent", "replies": {"data": [{"id": "r1"}]}}]
        replies = [{"id": "r1", "text": "Reply", "username": "child"}]
        with patch.object(scanner, "get_all", side_effect=[media, comments, replies]), patch.object(scanner.time, "sleep"):
            _, rows = scanner.fetch("token", "123")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["reply_to"], "parent")

    def test_write_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = os.path.join(tmp, "scan")
            json_path, csv_path = scanner.write_outputs(
                [{"id": "m1"}],
                [scanner.flatten({"id": "c1", "text": "Hi"}, {})],
                prefix,
            )
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(csv_path))


if __name__ == "__main__":
    unittest.main()
