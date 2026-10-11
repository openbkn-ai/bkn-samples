import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from installer.platform_version import read_backend_version


class PlatformVersionTest(unittest.TestCase):
    def read(self, payload, status=200):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.read.return_value = json.dumps(payload).encode()
        with patch("installer.platform_version.build_opener") as opener:
            opener.return_value.open.return_value = response
            version = read_backend_version("http://gateway.example/")
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, "http://gateway.example/api/bkn-backend/v1/health")
            self.assertIsNone(request.get_header("Authorization"))
            self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 5)
        return version

    def test_sdk_response_shapes_and_build_versions(self):
        for payload in ({"ServerVersion": "0.2.0"}, {"data": {"serverVersion": "0.2.0"}},
                        {"ServerVersion": "0.2.0-main.20261011000000.shaabc1234"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.read(payload), "0.2.0")

    def test_invalid_versions_and_responses_do_not_enable_installation(self):
        for payload in ([], {}, {"data": []}, {"ServerVersion": "main"},
                        {"ServerVersion": 2}, {"ServerVersion": "0.2"},
                        {"ServerVersion": "0.2.0-"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.read(payload), "")
        self.assertEqual(self.read({"ServerVersion": "0.2.0"}, status=503), "")

    def test_unavailable_backend_does_not_use_a_cached_version(self):
        with patch("installer.platform_version.build_opener") as opener:
            opener.return_value.open.side_effect = URLError("unavailable")
            self.assertEqual(read_backend_version("http://gateway.example"), "")

    def test_invalid_url_json_and_oversized_response(self):
        for url in ("", "http://[invalid", "file:///tmp/config", "http://user:password@gateway.example", "http://gateway.example?key=x"):
            self.assertEqual(read_backend_version(url), "")
        for content in (b"not JSON", b"a" * 65537):
            with patch("installer.platform_version.build_opener") as opener:
                response = MagicMock()
                response.__enter__.return_value = response
                response.status = 200
                response.read.return_value = content
                opener.return_value.open.return_value = response
                self.assertEqual(read_backend_version("http://gateway.example"), "")

    def test_redirect_is_not_followed(self):
        from installer.platform_version import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "Found", {}, "http://other.example"))
