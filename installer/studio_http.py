"""HTTP routes for the Studio sample catalog.

The process trusts bkn-safe for identity. ``is_admin`` from
``/api/safe/v1/me/permissions`` is the only install role.
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from installer.studio_api import ApiError

_LIST = re.compile(r"^/api/studio/samples$")
_CREATE = re.compile(r"^/api/studio/samples/(?P<sample>[a-z0-9-]{1,32})/installations$")
_RETRY = re.compile(
    r"^/api/studio/samples/(?P<sample>[a-z0-9-]{1,32})/installations/(?P<installation>[^/]+)/retry$"
)
_GET = re.compile(r"^/api/studio/samples/(?P<sample>[a-z0-9-]{1,32})/installations/(?P<installation>[^/]+)$")


def role_from_safe(me_status: int, permissions: dict | None) -> str:
    if me_status != 200:
        raise ApiError(401, "forbidden", "sign in to read the sample catalog")
    if isinstance(permissions, dict) and permissions.get("is_admin") is True:
        return "admin"
    return "user"


class StudioApp:
    def __init__(self, *, catalog, create, retry, get, authenticate):
        self.catalog = catalog
        self.create = create
        self.retry = retry
        self.get = get
        self.authenticate = authenticate


def dispatch(app: StudioApp, method: str, path: str, authorization: str | None, body: bytes) -> tuple[int, dict]:
    if body.strip():
        return 400, {"code": "install_failed", "message": "the request body must be empty"}
    action = _route(method, path)
    if action is None:
        return 404, {"code": "install_failed", "message": "unknown sample route"}
    try:
        role = app.authenticate(authorization)
        return action(app, role)
    except ApiError as exc:
        return exc.status, {"code": exc.code, "message": exc.message}


def _route(method: str, path: str):
    if _LIST.fullmatch(path) and method == "GET":
        return lambda app, role: (200, app.catalog(role))
    created = _CREATE.fullmatch(path)
    if created and method == "POST":
        sample = created.group("sample")
        return lambda app, role: (201, app.create(sample, role))
    retried = _RETRY.fullmatch(path)
    if retried and method == "POST":
        sample, installation = retried.group("sample"), retried.group("installation")
        return lambda app, role: (200, app.retry(sample, installation, role))
    current = _GET.fullmatch(path)
    if current and method == "GET":
        sample, installation = current.group("sample"), current.group("installation")
        return lambda app, role: (200, app.get(sample, installation, role))
    return None


class _Handler(BaseHTTPRequestHandler):
    app: StudioApp

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def log_message(self, fmt: str, *args) -> None:
        return

    def _handle(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length) if length else b""
        status, payload = dispatch(self.app, self.command, self.path.split("?", 1)[0], self.headers.get("Authorization"), body)
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def serve(app: StudioApp, host: str, port: int) -> ThreadingHTTPServer:
    _Handler.app = app
    server = ThreadingHTTPServer((host, port), _Handler)
    server.serve_forever()
    return server
