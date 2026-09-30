import json
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
    def test_token_is_sent_in_header_not_url(self):
        captured = {}

        def open_request(request, timeout):
            captured["url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["timeout"] = timeout
            return FakeResponse({"data": []})

        with patch.object(scanner.urllib.request, "urlopen", open_request):
            self.assertEqual(scanner._request_json("https://graph.facebook.com/v21.0/items?access_token=leaked&after=cursor", "dummy-token"), {"data": []})
        self.assertNotIn("dummy-token", captured["url"])
        self.assertNotIn("access_token", captured["url"])
        self.assertIn("after=cursor", captured["url"])
        self.assertEqual(captured["authorization"], "Bearer dummy-token")
        self.assertEqual(captured["timeout"], 60)

    def test_refuses_pagination_to_untrusted_host(self):
        with self.assertRaises(ValueError):
            scanner._request_json("https://example.test/steal", "dummy-token")

    def test_get_all_follows_pagination(self):
        pages = [
            {"data": [{"id": "one"}], "paging": {"next": "https://graph.example.test/next"}},
            {"data": [{"id": "two"}]},
        ]
        with patch.object(scanner, "_request_json", side_effect=pages), patch.object(scanner.time, "sleep"):
            result = scanner.get_all("account/media", {"limit": 50}, "dummy-token")
        self.assertEqual([item["id"] for item in result], ["one", "two"])

    def test_flatten_preserves_only_comment_record_fields(self):
        row = scanner.flatten(
            {"id": "comment-1", "text": "  Example\ncomment ", "username": "sample_user", "timestamp": "2026-01-01T00:00:00+0000", "like_count": 2},
            {"permalink": "https://instagram.example.test/p/example", "caption": "Sample caption"},
        )
        self.assertEqual(row["text"], "Example comment")
        self.assertEqual(row["username"], "sample_user")
        self.assertEqual(row["post_url"], "https://instagram.example.test/p/example")


if __name__ == "__main__":
    unittest.main()