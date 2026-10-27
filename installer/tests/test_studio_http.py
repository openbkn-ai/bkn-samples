import json
import threading
import unittest
from http.client import HTTPConnection

from installer.studio_api import ApiError
from installer.studio_http import StudioApp, authenticate_bearer, dispatch, role_from_safe
from http.server import ThreadingHTTPServer

from installer.studio_http import _Handler


def app(role: str = "admin", deploy=None) -> tuple[StudioApp, dict]:
    calls = {"deploy": 0, "create": 0}

    def authenticate(_authorization):
        if role == "":
            raise ApiError(401, "forbidden", "sign in to read the sample catalog")
        return role

    def create(sample, actor, _authorization=None):
        if actor != "admin":
            raise ApiError(403, "forbidden", "an administrator must install the sample")
        calls["create"] += 1
        if deploy:
            deploy(sample)
        calls["deploy"] += 1
        return {"id": "inst-supply-chain", "sample": sample, "status": "installed", "requestedBy": actor}

    built = StudioApp(
        catalog=lambda actor: {"samples": [{"name": "supply-chain", "installable": actor == "admin"}]},
        create=create,
        retry=lambda sample, installation, actor, _authorization=None: {"id": installation, "sample": sample, "status": "installed"},
        get=lambda sample, installation, _actor: {"id": installation, "sample": sample, "status": "installed"},
        authenticate=authenticate,
    )
    return built, calls


class StudioHttpTest(unittest.TestCase):
    def test_delete_reaches_handler_and_requires_admin(self):
        built, _ = app()
        deleted = []
        built.delete_package = lambda sample, role: deleted.append(sample) or {"deleted": True}
        _Handler.app = built
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            connection = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            connection.request("DELETE", "/api/studio/samples/world-cup/offline", headers={"Authorization": "Bearer t"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertTrue(json.loads(response.read())["deleted"])
            self.assertEqual(deleted, ["world-cup"])
            built.authenticate = lambda _: "user"
            connection.request("DELETE", "/api/studio/samples/world-cup/offline")
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
            self.assertEqual(deleted, ["world-cup"])
            connection.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_uninstall_is_admin_only_and_accepts_only_empty_body(self):
        built, _ = app()
        calls = []
        built.uninstall = lambda sample, installation, role, authorization: (calls.append((sample, installation, role)) or {"id": installation, "status": "uninstalling", "operation": "uninstall"})
        path = "/api/studio/samples/supply-chain/installations/inst-old/uninstall"
        status, result = dispatch(built, "POST", path, "Bearer t", b"{}")
        self.assertEqual(status, 202)
        self.assertEqual(result["operation"], "uninstall")
        built.authenticate = lambda _: "user"
        self.assertEqual(dispatch(built, "POST", path, "Bearer t", b"{}")[0], 403)
        self.assertEqual(len(calls), 1)
        built.authenticate = lambda _: "admin"
        self.assertEqual(dispatch(built, "POST", path, "Bearer t", b'{"ids":["unrelated"]}')[0], 400)
        self.assertEqual(len(calls), 1)

    def test_role_comes_from_safe_admin_flag(self):
        self.assertEqual(role_from_safe(200, {"is_admin": True}), "admin")
        self.assertEqual(role_from_safe(200, {"is_admin": False}), "user")
        with self.assertRaises(ApiError) as caught:
            role_from_safe(401, None)
        self.assertEqual(caught.exception.status, 401)

    def test_catalog_install_and_empty_body(self):
        built, calls = app()
        status, payload = dispatch(built, "GET", "/api/studio/samples", "Bearer t", b"")
        self.assertEqual(status, 200)
        self.assertTrue(payload["samples"][0]["installable"])

        status, payload = dispatch(built, "POST", "/api/studio/samples/supply-chain/installations", "Bearer t", b"")
        self.assertEqual(status, 202)
        self.assertEqual(payload["id"], "inst-supply-chain")
        self.assertEqual(calls["create"], 1)

        for extra in (b'{"image":"registry.example/x:1"}', b'{"database":{"host":"h"}}', b"[1]", b"not json"):
            status, body = dispatch(built, "POST", "/api/studio/samples/supply-chain/installations", "Bearer t", extra)
            self.assertEqual(status, 400)
            self.assertEqual(body["code"], "install_failed")
        self.assertEqual(calls["create"], 1)

    def test_browser_empty_object_body_is_accepted(self):
        built, calls = app()
        for empty in (b"{}", b" {} ", b"null"):
            status, _payload = dispatch(built, "POST", "/api/studio/samples/supply-chain/installations", "Bearer t", empty)
            self.assertEqual(status, 202)
        self.assertEqual(calls["create"], 3)

    def test_experience_set_route_reads_the_installed_set(self):
        built, _calls = app("user")
        path = "/api/studio/samples/experience-sets/supply_ontology_hand"
        status, payload = dispatch(built, "GET", path, "Bearer t", b"")
        self.assertEqual((status, payload["code"]), (404, "experience_set_unavailable"))
        built.experience = lambda network, role: {"knowledgeNetwork": network, "requestedBy": role}
        status, payload = dispatch(built, "GET", path, "Bearer t", b"")
        self.assertEqual((status, payload), (200, {"knowledgeNetwork": "supply_ontology_hand", "requestedBy": "user"}))
        status, _payload = dispatch(built, "POST", path, "Bearer t", b"")
        self.assertEqual(status, 404)

    def test_user_can_read_but_not_install(self):
        built, calls = app("user")
        status, payload = dispatch(built, "GET", "/api/studio/samples", "Bearer t", b"")
        self.assertEqual(status, 200)
        self.assertFalse(payload["samples"][0]["installable"])
        status, payload = dispatch(built, "POST", "/api/studio/samples/supply-chain/installations", "Bearer t", b"")
        self.assertEqual(status, 403)
        self.assertEqual(calls["create"], 0)

    def test_bearer_uses_the_safe_admin_flag(self):
        def fetch(path, _authorization):
            if path.startswith("/api/safe/v1/me/permissions"):
                return 200, {"is_admin": True}
            return 200, {"id": "admin"}

        self.assertEqual(authenticate_bearer(fetch, "Bearer token"), "admin")
        with self.assertRaises(ApiError):
            authenticate_bearer(fetch, None)

    def test_safe_http_failure_becomes_a_bounded_public_error(self):
        from urllib.error import HTTPError, URLError
        from unittest.mock import Mock
        for error, expected in [(HTTPError("http://safe/me", 401, "expired", {}, None), 401),
                                (HTTPError("http://safe/me", 403, "forbidden", {}, None), 401),
                                (HTTPError("http://safe/me", 500, "private-detail", {}, None), 503),
                                (URLError("private-detail"), 503), (TimeoutError(), 503)]:
            with self.subTest(expected=expected):
                fetch = Mock(side_effect=error)
                built, _ = app()
                built.authenticate = lambda auth: authenticate_bearer(fetch, auth)
                status, payload = dispatch(built, "GET", "/api/studio/samples", "Bearer expired", b"")
                self.assertEqual(status, expected)
                self.assertNotIn("private-detail", json.dumps(payload))
                self.assertEqual(fetch.call_count, 1)

    def test_expired_safe_token_returns_json_401_over_http(self):
        from urllib.error import HTTPError
        from unittest.mock import Mock
        built, _ = app()
        fetch = Mock(side_effect=HTTPError("http://safe/me", 401, "expired", {}, None))
        built.authenticate = lambda auth: authenticate_bearer(fetch, auth)
        _Handler.app = built
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            connection = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            connection.request("GET", "/api/studio/samples", headers={"Authorization": "Bearer expired"})
            response = connection.getresponse()
            self.assertEqual(response.status, 401)
            self.assertEqual(json.loads(response.read())["code"], "forbidden")
            connection.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_missing_token_is_rejected_over_http(self):
        built, _calls = app("")
        _Handler.app = built
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            connection = HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", "/api/studio/samples")
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 401)
            self.assertEqual(payload["code"], "forbidden")
            connection.request("GET", "/api/studio/samples/supply-chain/installations/inst-supply-chain/retry")
            missing = connection.getresponse()
            self.assertEqual(missing.status, 404)
            connection.request("GET", "/healthz")
            health = connection.getresponse()
            self.assertEqual(health.status, 200)
            health.read()
            connection.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
