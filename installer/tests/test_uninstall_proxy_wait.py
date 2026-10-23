"""Current main uses network cascade deletion; only its pending proxy is retried."""
import io
import json
import unittest
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from installer import uninstall as u
from installer.studio_api import ApiError


PATH = "/api/bkn-backend/v1/knowledge-networks/owned-network"
CODE = "BknBackend.KnowledgeNetwork.InternalError"
PENDING = "knowledge network proxy synchronization is pending"


def http_error(status=409, details=PENDING, code=CODE):
    return HTTPError("http://platform" + PATH, status, "Rejected", {},
                     io.BytesIO(json.dumps({"error_code": code, "error_details": details}).encode()))


class ProxyWaitTest(unittest.TestCase):
    def test_real_http_pending_response_converges_without_losing_auth(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                calls.append(("GET", self.path, self.headers.get("Authorization")))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"tags":["owned"]}')

            def do_DELETE(self):
                calls.append(("DELETE", self.path, self.headers.get("Authorization")))
                attempts = sum(method == "DELETE" for method, _, _ in calls)
                self.send_response(409 if attempts < 4 else 204)
                self.end_headers()
                if attempts < 4:
                    self.wfile.write(json.dumps({"error_code": CODE, "error_details": PENDING}).encode())

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict("os.environ", {"BKN_BASE_URL": f"http://127.0.0.1:{server.server_port}"}), \
                 patch.object(u.time, "sleep"):
                u._delete_network(u.platform_client("Bearer synthetic"), PATH, {"owned"}, u.time.monotonic() + 300)
            self.assertEqual([method for method, _, _ in calls], ["DELETE", "GET", "DELETE", "GET", "DELETE", "GET", "DELETE"])
            self.assertTrue(all(path == PATH and auth == "Bearer synthetic" for _, path, auth in calls))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_pending_preserves_safe_diagnostics_without_generic_retry(self):
        with patch.dict("os.environ", {"BKN_BASE_URL": "http://platform"}), \
             patch.object(u, "urlopen", side_effect=http_error()) as request, \
             patch.object(u.time, "sleep") as sleep:
            with self.assertRaises(ApiError) as raised:
                u.platform_client("Bearer synthetic")("DELETE", PATH)
        self.assertEqual(raised.exception.code, "uninstall_proxy_sync_pending")
        self.assertEqual(raised.exception.upstream, {"status": 409, "code": CODE, "reason": "proxy_sync_pending"})
        self.assertEqual(request.call_count, 1)
        sleep.assert_not_called()

    def test_unsafe_upstream_details_are_never_exposed(self):
        with patch.dict("os.environ", {"BKN_BASE_URL": "http://platform"}), \
             patch.object(u, "urlopen", side_effect=http_error(403, "Authorization: Bearer secret-value")):
            with self.assertRaises(ApiError) as raised:
                u.platform_client("Bearer synthetic")("DELETE", PATH)
        self.assertEqual(raised.exception.upstream["status"], 403)
        self.assertIn(CODE, raised.exception.message)
        self.assertNotIn("secret-value", str(raised.exception.__dict__))

    def test_pending_detail_on_other_resource_is_not_network_wait(self):
        with patch.dict("os.environ", {"BKN_BASE_URL": "http://platform"}), \
             patch.object(u, "urlopen", side_effect=[http_error(), http_error()]) as request, \
             patch.object(u.time, "sleep"):
            with self.assertRaises(ApiError) as raised:
                u.platform_client("Bearer synthetic")("DELETE", "/api/vega-backend/v1/catalogs/owned")
        self.assertEqual(raised.exception.code, "uninstall_failed")
        self.assertEqual(request.call_count, 2)

    def test_network_wait_rechecks_ownership_and_uses_authoritative_delete(self):
        pending = u.PlatformFailure(409, CODE, proxy_pending=True)
        api = Mock(side_effect=[pending, {"tags": ["owned"]}, pending, {"tags": ["owned"]}, {}])
        with patch.object(u.time, "sleep") as sleep:
            u._delete_network(api, PATH, {"owned"}, u.time.monotonic() + 300)
        self.assertEqual([c.args[0] for c in api.call_args_list], ["DELETE", "GET", "DELETE", "GET", "DELETE"])
        self.assertEqual(sleep.call_count, 2)

    def test_network_wait_does_not_delete_replacement(self):
        api = Mock(side_effect=[u.PlatformFailure(409, CODE, proxy_pending=True), {"tags": ["foreign"]}])
        with patch.object(u.time, "sleep"), self.assertRaises(ApiError) as raised:
            u._delete_network(api, PATH, {"owned"}, u.time.monotonic() + 300)
        self.assertEqual(raised.exception.code, "ownership_conflict")
        self.assertEqual(api.call_count, 2)

    def test_removed_network_during_wait_is_success(self):
        api = Mock(side_effect=[u.PlatformFailure(409, CODE, proxy_pending=True), None])
        with patch.object(u.time, "sleep"):
            u._delete_network(api, PATH, {"owned"}, u.time.monotonic() + 300)
        self.assertEqual(api.call_count, 2)

    def test_wait_has_attempt_bound_even_without_clock_advance(self):
        def call(method, path):
            if method == "GET":
                return {"tags": ["owned"]}
            raise u.PlatformFailure(409, CODE, proxy_pending=True)
        api = Mock(side_effect=call)
        with patch.object(u.time, "sleep") as sleep, self.assertRaises(ApiError) as raised:
            u._delete_network(api, PATH, {"owned"}, u.time.monotonic() + 300)
        self.assertEqual(raised.exception.code, "uninstall_proxy_sync_timeout")
        self.assertEqual(raised.exception.upstream["status"], 409)
        self.assertLessEqual(sleep.call_count, 59)

    def test_non_pending_error_is_not_retried(self):
        api = Mock(side_effect=u.PlatformFailure(403, CODE))
        with patch.object(u.time, "sleep") as sleep, self.assertRaises(ApiError):
            u._delete_network(api, PATH, {"owned"}, u.time.monotonic() + 300)
        api.assert_called_once_with("DELETE", PATH)
        sleep.assert_not_called()

    def test_expired_deadline_never_deletes(self):
        api = Mock()
        with self.assertRaises(ApiError):
            u._delete_network(api, PATH, {"owned"}, u.time.monotonic() - 1)
        api.assert_not_called()

    def test_slow_request_exhausts_budget_without_starting_another(self):
        api = Mock(side_effect=u.PlatformFailure(409, CODE, proxy_pending=True))
        with patch.object(u.time, "monotonic", side_effect=[0, 0, 121]), \
             patch.object(u.time, "sleep") as sleep, self.assertRaises(ApiError) as raised:
            u._delete_network(api, PATH, {"owned"}, 300)
        self.assertEqual(raised.exception.code, "uninstall_proxy_sync_timeout")
        api.assert_called_once_with("DELETE", PATH)
        sleep.assert_not_called()

    def test_oversized_or_malformed_error_body_is_not_reflected(self):
        for body in [b"secret=" + b"x" * 17000, b"not-json-secret", b"[]", b"null"]:
            with self.subTest(body_length=len(body)), \
                 patch.dict("os.environ", {"BKN_BASE_URL": "http://platform"}), \
                 patch.object(u, "urlopen", side_effect=HTTPError("http://platform", 502, "Rejected", {}, io.BytesIO(body))):
                with self.assertRaises(ApiError) as raised:
                    u.platform_client("Bearer synthetic")("DELETE", PATH)
                self.assertEqual(raised.exception.upstream, {"status": 502})
                self.assertNotIn("secret", raised.exception.message)


if __name__ == "__main__":
    unittest.main()
