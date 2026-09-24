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

    def create(sample, actor):
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
        retry=lambda sample, installation, actor: {"id": installation, "sample": sample, "status": "installed"},
        get=lambda sample, installation, _actor: {"id": installation, "sample": sample, "status": "installed"},
        authenticate=authenticate,
    )
    return built, calls


class StudioHttpTest(unittest.TestCase):
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
        self.assertEqual(status, 201)
        self.assertEqual(payload["id"], "inst-supply-chain")
        self.assertEqual(calls["create"], 1)

        status, body = dispatch(built, "POST", "/api/studio/samples/supply-chain/installations", "Bearer t", b"{}")
        self.assertEqual(status, 400)
        self.assertEqual(body["code"], "install_failed")
        self.assertEqual(calls["create"], 1)

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
