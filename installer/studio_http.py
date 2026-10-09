"""HTTP routes for the Studio sample catalog.

The process trusts bkn-safe for identity. ``is_admin`` from
``/api/safe/v1/me/permissions`` is the only install role.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from installer.studio_api import ApiError

_LIST = re.compile(r"^/api/studio/samples$")
_REFRESH = re.compile(r"^/api/studio/samples/refresh$")
_CREATE = re.compile(r"^/api/studio/samples/(?P<sample>[a-z0-9-]{1,32})/installations$")
_RETRY = re.compile(
    r"^/api/studio/samples/(?P<sample>[a-z0-9-]{1,32})/installations/(?P<installation>[^/]+)/retry$"
)
_GET = re.compile(r"^/api/studio/samples/(?P<sample>[a-z0-9-]{1,32})/installations/(?P<installation>[^/]+)$")
_NOTES = re.compile(r"^/api/studio/samples/(?P<sample>[a-z0-9-]{1,63})/versions/(?P<version>[0-9]+\.[0-9]+\.[0-9]+)/release-notes$")


def role_from_safe(me_status: int, permissions: dict | None) -> str:
    if me_status != 200:
        raise ApiError(401, "forbidden", "sign in to read the sample catalog")
    if isinstance(permissions, dict) and permissions.get("is_admin") is True:
        return "admin"
    return "user"


class StudioApp:
    def __init__(self, *, catalog, create, retry, get, authenticate, notes=None, history=None, refresh=None, create_selected=None, import_package=None):
        self.catalog = catalog
        self.create = create
        self.retry = retry
        self.get = get
        self.authenticate = authenticate
        self.notes = notes
        self.history = history
        self.refresh = refresh
        self.create_selected = create_selected
        self.import_package = import_package


def _empty_body(body: bytes) -> bool:
    """A browser client sends {} for a POST without parameters. Any real field is still refused."""
    text = body.strip()
    if not text:
        return True
    try:
        return json.loads(text) in ({}, None)
    except ValueError:
        return False


def dispatch(app: StudioApp, method: str, path: str, authorization: str | None, body: bytes) -> tuple[int, dict]:
    try:
        payload = json.loads(body) if body.strip() else {}
    except (ValueError, UnicodeDecodeError):
        return 400, {"code": "install_failed", "message": "invalid request JSON"}
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return 400, {"code": "install_failed", "message": "request body must be an object"}
    url = urlsplit(path)
    is_create = method == "POST" and _CREATE.fullmatch(url.path)
    if payload and (not is_create or set(payload) != {"version", "manifestSha256"}
                    or not all(isinstance(v, str) and v for v in payload.values())):
        return 400, {"code": "install_failed", "message": "expected version and manifestSha256, or an empty body"}
    query = parse_qs(url.query, keep_blank_values=True)
    if query and (not _NOTES.fullmatch(url.path) or set(query) != {"locale"}
                  or len(query["locale"]) != 1
                  or not re.fullmatch(r"[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", query["locale"][0])):
        return 400, {"code": "install_failed", "message": "invalid query parameters"}
    action = _route(method, url.path, payload, query.get("locale", ["zh-CN"])[0])
    if action is None:
        return 404, {"code": "install_failed", "message": "unknown sample route"}
    try:
        role = app.authenticate(authorization)
        return action(app, role, authorization)
    except ApiError as exc:
        return exc.status, {"code": exc.code, "message": exc.message}


def _route(method: str, path: str, payload: dict | None = None, locale: str = "zh-CN"):
    if _LIST.fullmatch(path) and method == "GET":
        return lambda app, role, _authorization: (200, app.catalog(role))
    if _REFRESH.fullmatch(path) and method == "POST":
        return lambda app, role, _authorization: (200, app.refresh(role)) if app.refresh else (404, {"code": "source_unavailable", "message": "refresh unavailable"})
    created = _CREATE.fullmatch(path)
    if created and method == "GET":
        sample = created.group("sample")
        return lambda app, role, _authorization: (200, app.history(sample, role)) if app.history else (404, {"code": "install_failed", "message": "history unavailable"})
    if created and method == "POST":
        sample = created.group("sample")
        def create(app, role, authorization):
            if role != "admin":
                raise ApiError(403, "forbidden", "an administrator must install the sample")
            if payload:
                catalog = app.catalog(role)
                item = next((item for item in catalog["samples"] if item.get("name") == sample), None)
                if catalog.get("sourceRejected") or not item:
                    raise ApiError(409, "source_rejected", "sample is not currently installable")
                if app.create_selected:
                    return 202, app.create_selected(sample, role, authorization, payload["version"], payload["manifestSha256"])
                else:
                    if not item.get("installable"):
                        raise ApiError(409, "source_rejected", "sample is not currently installable")
                    if payload["version"] != item.get("version") or payload["manifestSha256"] != item.get("manifestSha256"):
                        raise ApiError(409, "version_changed", "sample version or manifest changed; confirm again")
            return 202, app.create(sample, role, authorization)
        return create
    notes = _NOTES.fullmatch(path)
    if notes and method == "GET":
        return lambda app, role, _authorization: (200, app.notes(notes.group("sample"), notes.group("version"), role, locale)) if app.notes else (404, {"code": "release_notes_unavailable", "message": "version notes unavailable"})
    retried = _RETRY.fullmatch(path)
    if retried and method == "POST":
        sample, installation = retried.group("sample"), retried.group("installation")
        return lambda app, role, authorization: (202, app.retry(sample, installation, role, authorization))
    current = _GET.fullmatch(path)
    if current and method == "GET":
        sample, installation = current.group("sample"), current.group("installation")
        return lambda app, role, _authorization: (200, app.get(sample, installation, role))
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
        path = self.path
        if self.command == "GET" and path == "/healthz":
            encoded = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = -1
        importing = self.command == "POST" and self.path == "/api/studio/samples/import"
        if importing:
            self._import(length)
            return
        if not 0 <= length <= 64 * 1024:
            self._reply(413, {"code": "invalid_package", "message": "request body exceeds size limit"})
            return
        body = self.rfile.read(length) if length else b""
        status, payload = dispatch(self.app, self.command, path, self.headers.get("Authorization"), body)
        self._reply(status, payload)

    def _import(self, length):
        try:
            role = self.app.authenticate(self.headers.get("Authorization"))
            if role != "admin":
                raise ApiError(403, "forbidden", "an administrator must import the sample")
            if not self.app.import_package:
                raise ApiError(404, "import_unavailable", "offline import is unavailable")
            if self.headers.get("Transfer-Encoding") or not 0 < length <= 128 * 1024 * 1024:
                raise ApiError(413, "invalid_package", "package must be at most 128 MiB")
            if self.headers.get("Content-Type", "").split(";")[0] != "application/gzip":
                raise ApiError(415, "invalid_package", "expected application/gzip")
            self.connection.settimeout(60)
            with tempfile.TemporaryDirectory() as temporary:
                archive = Path(temporary) / "package.tar.gz"
                with archive.open("xb") as output:
                    remaining = length
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ApiError(400, "invalid_package", "incomplete package upload")
                        output.write(chunk)
                        remaining -= len(chunk)
                payload = self.app.import_package(archive, role)
            self._reply(201, payload)
        except ApiError as error:
            self._reply(error.status, {"code": error.code, "message": error.message})
        except (OSError, ValueError):
            self._reply(400, {"code": "invalid_package", "message": "package upload failed"})

    def _reply(self, status, payload):
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


def build_app(*, list_samples, create_installation, retry_installation, get_installation, authenticate, release_notes=None, installation_history=None, refresh_catalog=None, create_selected=None, import_package=None) -> StudioApp:
    return StudioApp(
        catalog=list_samples,
        create=create_installation,
        retry=retry_installation,
        get=get_installation,
        authenticate=authenticate,
        notes=release_notes,
        history=installation_history,
        refresh=refresh_catalog,
        create_selected=create_selected,
        import_package=import_package,
    )


def main() -> None:
    import os
    import platform
    from pathlib import Path
    from urllib.request import Request, urlopen

    from installer.runtime import deploy as deploy_database_sample
    from installer.runtime import install_sample, kubectl_run, process_run, retry_sample
    from installer.studio_api import (get_sample_installation, get_sample_release_notes,
                                      list_sample_installations, list_samples, load_indexes,
                                      _read_state, _write_installing, _installation_id, ApiError)
    from installer.release import merge_catalog
    from installer.catalog_source import OfficialCatalog
    from installer.state_store import write_json
    from installer.task_runner import InstallationRunner
    from installer.deploy_database import configured_image_ref
    from installer.deploy_database import deploy_database
    from installer.remote_installation import RemoteInstallation
    from installer.remote_catalog import merge_remote
    from installer.offline_bundle import OfflinePackages

    root = Path(os.environ.get("BKN_SAMPLES_ROOT", "/opt/bkn-samples"))
    state_dir = Path(os.environ.get("BKN_SAMPLE_STATE_DIR", "/var/lib/bkn-samples/state"))
    image_index = Path(os.environ.get("BKN_SAMPLE_IMAGE_INDEX", str(root / "manifest-index.json")))
    safe_url = os.environ.get("BKN_SAFE_URL", "http://bkn-safe:3000").rstrip("/")
    version, image, repo = load_indexes(root, image_index)
    data_image_ref = configured_image_ref()
    source = OfficialCatalog(state_dir, root / "protocol/draft/schemas/catalog.schema.json")
    runner = InstallationRunner(state_dir, [item["name"] for item in image.get("samples", []) if item.get("name")])
    runner.recover_interrupted()
    remote = RemoteInstallation(root, state_dir, os.environ.get("BKN_SAMPLE_PLATFORM_VERSION", ""),
                                {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64"}.get(platform.machine(), platform.machine()),
                                os.environ.get("BKN_SAMPLE_PLATFORM_CAPABILITIES", "").split(","),
                                os.environ.get("BKN_SAMPLE_EXECUTOR_IMAGE_REF", ""))
    offline = OfflinePackages(root, state_dir, remote)

    def fetch(path: str, authorization: str):
        request = Request(safe_url + path, headers={"Authorization": authorization})
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def catalog(role: str) -> dict:
        result = list_samples(
            pinned_version=version,
            image_index=image,
            repo_index=repo,
            state_dir=state_dir,
            actor_role=role,
        )
        merge_remote(result, source.entries(), state_dir, role, remote)
        offline.merge(result, role)
        result["sourceRefresh"] = source.metadata()
        return result

    def refresh(role):
        if role not in {"admin", "user"}:
            raise ApiError(401, "forbidden", "sign in to refresh the sample catalog")
        result = source.refresh()
        response = catalog(role)
        response["sourceRefresh"].update(result)
        return response

    def release_notes(sample, requested_version, role, locale):
        try:
            return get_sample_release_notes(sample=sample, version=requested_version, actor_role=role,
                locale=locale, pinned_version=version, image_index=image, repo_index=repo, state_dir=state_dir)
        except ApiError as error:
            if error.status != 404:
                raise
            return source.notes(sample, requested_version, locale)

    def prepare_create(sample: str, role: str, authorization: str | None = None) -> None:
        if role != "admin":
            raise ApiError(403, "forbidden", "an administrator must install the sample")
        merged = merge_catalog(version, image, repo)
        item = next((item for item in merged["samples"] if item.get("name") == sample), None)
        if merged["sourceRejected"] or not item or item.get("status") == "unavailable":
            raise ApiError(409, "source_rejected", "sample is not currently installable")
        current = _read_state(state_dir, sample)
        if current and current.get("status") in {"installed", "failed", "installing"}:
            code = ("already_installed" if current["status"] == "installed" else
                    "already_installing" if current["status"] == "installing" else "use_retry")
            raise ApiError(409, code, "an installation already exists")
        _write_installing(state_dir, sample, version, item.get("releaseNotes"), item.get("manifestSha256"),
                          data_image_ref)

    def perform_create(sample, role, authorization):
        return install_sample(
            sample=sample,
            actor_role=role,
            state_dir=state_dir,
            root=root,
            version=version,
            deploy=lambda name: deploy_database_sample(root, name),
            kubectl=kubectl_run,
            run=process_run,
            authorization=authorization,
        )

    def prepare_retry(sample: str, installation: str, role: str, authorization: str | None = None) -> None:
        current = _read_state(state_dir, sample) or {}
        merged = merge_catalog(version, image, repo)
        item = next((item for item in merged["samples"] if item.get("name") == sample), None)
        if merged["sourceRejected"] or not item or item.get("status") == "unavailable":
            raise ApiError(409, "source_rejected", "sample is not currently installable")
        if current.get("manifestSha256") and current["manifestSha256"] != item.get("manifestSha256"):
            raise ApiError(409, "version_changed", "retry requires the original manifest")
        if not current or _installation_id(current) != installation:
            raise ApiError(404, "install_failed", "installation not found")
        if current.get("status") != "failed":
            raise ApiError(409, "already_installed" if current.get("status") == "installed" else "already_installing",
                           "only a failed installation can be retried")
        if current.get("version") != version or ("dataImageRef" in current and current["dataImageRef"] != data_image_ref):
            raise ApiError(409, "version_changed", "retry requires the original installed artifacts and data image")
        current["status"] = "installing"
        current.pop("error", None)
        current.pop("finishedAt", None)
        for stage, status in list(current.get("stages", {}).items()):
            if status == "failed":
                current["stages"][stage] = "running"
        write_json(state_dir / f"{sample}.json", current)

    def perform_retry(sample, installation, role, authorization):
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
            authorization=authorization,
            accepted=True,
        )

    def create(sample, role, authorization=None):
        if role != "admin":
            raise ApiError(403, "forbidden", "an administrator must install the sample")
        return runner.submit(sample, lambda: prepare_create(sample, role, authorization),
                             lambda: perform_create(sample, role, authorization))

    def execute_remote(sample, role, authorization, retrying=False):
        def install_fixed(bundle_root, fixed_version, fixed_image, is_retry):
            arguments = dict(sample=sample, actor_role=role, state_dir=state_dir, root=bundle_root,
                version=fixed_version, deploy=lambda name: deploy_database(bundle_root, name, kubectl_run,
                    data_image_ref=fixed_image, require_ownership=True), kubectl=kubectl_run,
                run=process_run, authorization=authorization)
            if is_retry:
                return retry_sample(**arguments, installation_id=_installation_id(_read_state(state_dir, sample)),
                                    accepted=True, data_image_ref=fixed_image)
            return install_sample(**arguments)
        return remote.execute(sample, install_fixed, retry=retrying)

    def create_selected(sample, role, authorization, requested_version, requested_digest):
        if role != "admin":
            raise ApiError(403, "forbidden", "an administrator must install the sample")
        bundled = next((i for i in merge_catalog(version, image, repo)["samples"] if i["name"] == sample), None)
        if bundled and requested_version == version and requested_digest == bundled.get("manifestSha256"):
            return create(sample, role, authorization)
        offline_release = offline.find(sample)
        if offline_release and offline_release["version"] == requested_version:
            if requested_digest != offline_release["manifestSha256"]:
                raise ApiError(409, "version_changed", "sample version or manifest changed; confirm again")
            runner.register(sample)
            return runner.submit(sample, lambda: offline.prepare(offline_release),
                                 lambda: offline.execute(offline_release, lambda bundle_root, fixed_version, fixed_image, retry: install_sample(
                                     sample=sample, actor_role=role, state_dir=state_dir, root=bundle_root,
                                     version=fixed_version, deploy=lambda name: deploy_database(bundle_root, name, kubectl_run,
                                         data_image_ref=fixed_image, require_ownership=True), kubectl=kubectl_run,
                                     run=process_run, authorization=authorization)))
        entry = next((e for e in source.entries() if e["sampleId"] == sample and e["version"] == requested_version), None)
        if not entry or requested_digest != entry["manifest"]["digest"].removeprefix("sha256:"):
            raise ApiError(409, "version_changed", "sample version or manifest changed; confirm again")
        runner.register(sample)
        return runner.submit(sample, lambda: remote.prepare(entry), lambda: execute_remote(sample, role, authorization))

    def retry(sample, installation, role, authorization=None):
        if role != "admin":
            raise ApiError(403, "forbidden", "an administrator must install the sample")
        current = _read_state(state_dir, sample) or {}
        if current.get("offlineRelease"):
            release = offline.find(sample)
            if not release:
                raise ApiError(409, "source_rejected", "offline package is unavailable")
            runner.register(sample)
            return runner.submit(sample, lambda: offline.prepare(release, retry=True),
                                 lambda: offline.execute(release, lambda bundle_root, fixed_version, fixed_image, retry: install_sample(
                                     sample=sample, actor_role=role, state_dir=state_dir, root=bundle_root,
                                     version=fixed_version, deploy=lambda name: deploy_database(bundle_root, name, kubectl_run,
                                         data_image_ref=fixed_image, require_ownership=True), kubectl=kubectl_run,
                                     run=process_run, authorization=authorization), retry=True))
        if current.get("remoteRelease"):
            fixed = current["remoteRelease"]["entry"]
            if any(e["sampleId"] == sample and e["version"] == fixed["version"] and e["releaseStatus"] == "withdrawn"
                   for e in source.entries()):
                raise ApiError(409, "release_withdrawn", "release has been withdrawn")
            runner.register(sample)
            return runner.submit(sample, lambda: remote.prepare_retry(sample, installation),
                                 lambda: execute_remote(sample, role, authorization, True))
        return runner.submit(sample, lambda: prepare_retry(sample, installation, role, authorization),
                             lambda: perform_retry(sample, installation, role, authorization))

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
        release_notes=release_notes,
        refresh_catalog=refresh,
        create_selected=create_selected,
        import_package=lambda archive, role: offline.import_package(archive, role),
        installation_history=lambda sample, role: list_sample_installations(
            sample=sample, state_dir=state_dir, actor_role=role),
    )
    serve(app, os.environ.get("BKN_SAMPLE_HTTP_HOST", "0.0.0.0"), int(os.environ.get("BKN_SAMPLE_HTTP_PORT", "8080")))


if __name__ == "__main__":
    main()
