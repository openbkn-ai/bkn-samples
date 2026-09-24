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
        path = self.path.split("?", 1)[0]
        if self.command == "GET" and path == "/healthz":
            encoded = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length) if length else b""
        status, payload = dispatch(self.app, self.command, path, self.headers.get("Authorization"), body)
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


def authenticate_bearer(fetch, authorization: str | None) -> str:
    """``fetch(path, authorization)`` returns ``(status, json)`` from bkn-safe."""
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "forbidden", "sign in to read the sample catalog")
    me_status, _me = fetch("/api/safe/v1/me", authorization)
    perm_status, permissions = fetch("/api/safe/v1/me/permissions?scope=type", authorization)
    if me_status != 200 or perm_status != 200:
        raise ApiError(401, "forbidden", "sign in to read the sample catalog")
    return role_from_safe(me_status, permissions if isinstance(permissions, dict) else None)


def build_app(*, list_samples, create_installation, retry_installation, get_installation, authenticate) -> StudioApp:
    return StudioApp(
        catalog=list_samples,
        create=create_installation,
        retry=retry_installation,
        get=get_installation,
        authenticate=authenticate,
    )


def main() -> None:
    import os
    from pathlib import Path
    from urllib.request import Request, urlopen

    from installer.runtime import deploy as deploy_database_sample
    from installer.runtime import install_sample, kubectl_run, process_run, retry_sample
    from installer.studio_api import get_sample_installation, list_samples, load_indexes

    root = Path(os.environ.get("BKN_SAMPLES_ROOT", "/opt/bkn-samples"))
    state_dir = Path(os.environ.get("BKN_SAMPLE_STATE_DIR", "/var/lib/bkn-samples/state"))
    image_index = Path(os.environ.get("BKN_SAMPLE_IMAGE_INDEX", str(root / "manifest-index.json")))
    safe_url = os.environ.get("BKN_SAFE_URL", "http://bkn-safe:3000").rstrip("/")
    version, image, repo = load_indexes(root, image_index)

    def fetch(path: str, authorization: str):
        request = Request(safe_url + path, headers={"Authorization": authorization})
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def catalog(role: str) -> dict:
        return list_samples(
            pinned_version=version,
            image_index=image,
            repo_index=repo,
            state_dir=state_dir,
            actor_role=role,
        )

    def create(sample: str, role: str) -> dict:
        return install_sample(
            sample=sample,
            actor_role=role,
            state_dir=state_dir,
            root=root,
            version=version,
            deploy=lambda name: deploy_database_sample(root, name),
            kubectl=kubectl_run,
            run=process_run,
        )

    def retry(sample: str, installation: str, role: str) -> dict:
        return retry_sample(
            sample=sample,
            installation_id=installation,
            actor_role=role,
            state_dir=state_dir,
            root=root,
            version=version,
            deploy=lambda name: deploy_database_sample(root, name),
            kubectl=kubectl_run,
            run=process_run,
        )

    app = build_app(
        list_samples=catalog,
        create_installation=create,
        retry_installation=retry,
        get_installation=lambda sample, installation, role: get_sample_installation(
            sample=sample,
            installation_id=installation,
            state_dir=state_dir,
            actor_role=role,
        ),
        authenticate=lambda authorization: authenticate_bearer(fetch, authorization),
    )
    serve(app, os.environ.get("BKN_SAMPLE_HTTP_HOST", "0.0.0.0"), int(os.environ.get("BKN_SAMPLE_HTTP_PORT", "8080")))


if __name__ == "__main__":
    main()
