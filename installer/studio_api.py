"""Studio catalog HTTP API. Auth is the caller's role; this module does not call kubectl."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from installer.control_plane import ControlError, create_installation, note_database_ready, retry_installation, timestamp
from installer.state_store import write_json
from installer.contract import read_version
from installer.release import merge_catalog

NAME_RE = re.compile(r"^[a-z0-9-]{1,32}$")
STAGES = (
    ("database", "准备样例库"),
    ("discover", "扫描数据资源"),
    ("knowledge", "导入并绑定知识网络"),
    ("capabilities", "发布能力"),
    ("verify", "冒烟验收"),
)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def list_samples(*, pinned_version: str, image_index: dict, repo_index: dict, state_dir: Path, actor_role: str) -> dict:
    _require_role(actor_role)
    merged = merge_catalog(pinned_version, image_index, repo_index)
    samples = [
        _card(item, pinned_version, _read_state(state_dir, item.get("name", "")), actor_role, merged["sourceRejected"])
        for item in merged["samples"]
        if item.get("name")
    ]
    return {
        "sourceRepo": repo_index.get("sourceRepo") or image_index.get("sourceRepo") or "",
        "sourceRejected": merged["sourceRejected"],
        "version": pinned_version,
        "samples": samples,
    }


def create_sample_installation(
    *,
    sample: str,
    actor_role: str,
    state_dir: Path,
    version: str,
    database: dict,
    openbkn,
    hook_runner,
    deploy,
    expected_tables: int,
    knowledge_network: dict,
) -> dict:
    _require_sample(sample)
    if actor_role != "admin":
        raise ApiError(403, "forbidden", "an administrator must install the sample")
    current = _read_state(state_dir, sample)
    if not current or current.get("status") not in {"installed", "failed"}:
        _write_installing(state_dir, sample, version)
    try:
        deploy(sample)
    except Exception as exc:
        code = getattr(exc, "code", "database_not_ready")
        message = getattr(exc, "message", str(exc))
        _write_failed(state_dir, sample, version, code, message)
        raise ApiError(409 if code in {"already_installed", "use_retry"} else 500, code, message) from exc
    current = _read_state(state_dir, sample)
    if not current or current.get("status") not in {"installed", "failed"}:
        note_database_ready(state_dir, sample, version)
    try:
        record = create_installation(
            sample=sample,
            version=version,
            actor_role=actor_role,
            database=database,
            state_dir=state_dir,
            openbkn=openbkn,
            hook_runner=hook_runner,
            expected_tables=expected_tables,
            knowledge_network=knowledge_network,
        )
    except ControlError as exc:
        raise _api_error(exc) from exc
    return installation_view(record, actor_role)


def retry_sample_installation(
    *,
    sample: str,
    installation_id: str,
    actor_role: str,
    state_dir: Path,
    version: str,
    database: dict,
    openbkn,
    hook_runner,
    deploy,
    expected_tables: int,
    knowledge_network: dict,
) -> dict:
    _require_sample(sample)
    current = _read_state(state_dir, sample)
    if not current or _installation_id(current) != installation_id:
        raise ApiError(404, "install_failed", "installation not found")
    if actor_role != "admin":
        raise ApiError(403, "forbidden", "an administrator must install the sample")
    try:
        deploy(sample)
        record = retry_installation(
            sample=sample,
            version=version,
            actor_role=actor_role,
            database=database,
            state_dir=state_dir,
            openbkn=openbkn,
            hook_runner=hook_runner,
            expected_tables=expected_tables,
            knowledge_network=knowledge_network,
        )
    except ControlError as exc:
        raise _api_error(exc) from exc
    return installation_view(record, actor_role)


def get_sample_installation(*, sample: str, installation_id: str, state_dir: Path, actor_role: str) -> dict:
    _require_role(actor_role)
    _require_sample(sample)
    current = _read_state(state_dir, sample)
    if not current or _installation_id(current) != installation_id:
        raise ApiError(404, "install_failed", "installation not found")
    return installation_view(current, actor_role)


def list_sample_installations(*, sample: str, state_dir: Path, actor_role: str) -> dict:
    _require_role(actor_role)
    _require_sample(sample)
    record = _read_state(state_dir, sample)
    # v1alpha1 stores only one record. Do not invent previously overwritten history.
    return {"items": [installation_view(record, actor_role)] if record else [],
            "historyComplete": False}


def get_sample_release_notes(*, sample: str, version: str, actor_role: str,
                             pinned_version: str, image_index: dict, repo_index: dict,
                             state_dir: Path, locale: str = "zh-CN") -> dict:
    _require_role(actor_role)
    _require_sample(sample)
    record = _read_state(state_dir, sample)
    notes = (record or {}).get("releaseNotesSnapshot")
    if not isinstance(notes, dict) or notes.get("version") != version:
        merged = merge_catalog(pinned_version, image_index, repo_index)
        item = next((item for item in merged["samples"] if item.get("name") == sample), None)
        if version != pinned_version or merged["sourceRejected"] or not item or item.get("status") == "unavailable":
            raise ApiError(404, "release_notes_unavailable", "version notes are unavailable")
        notes = item.get("releaseNotes")
    if not isinstance(notes, dict) or notes.get("version") != version:
        raise ApiError(404, "release_notes_unavailable", "version notes are unavailable")
    documents = notes.get("documents") or []
    document = next((d for d in documents if d.get("locale") == locale), None)
    if document is None:
        document = next((d for d in documents if d.get("locale") == notes.get("defaultLocale")), None)
    if document is None:
        raise ApiError(404, "release_notes_unavailable", "version notes are unavailable")
    content = document.get("content")
    if not isinstance(content, str) or not content.strip() or document.get("digest") != "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest():
        raise ApiError(500, "release_notes_unavailable", "version notes digest does not match")
    return {"sample": sample, "version": version, "resolvedLocale": document["locale"],
            "content": document["content"], "digest": document["digest"]}


def installation_view(record: dict, actor_role: str) -> dict:
    error = record.get("error") if isinstance(record.get("error"), dict) else None
    failed_at = _failed_stage(record) if record.get("status") == "failed" else ""
    stages = []
    running_assigned = False
    for stage_id, name in STAGES:
        state = (record.get("stages") or {}).get(stage_id)
        if stage_id == "database" and state == "failed":
            stages.append({"id": stage_id, "name": name, "state": "failed"})
            continue
        if stage_id == "database" and record.get("status") == "installing" and state != "succeeded":
            stages.append({"id": stage_id, "name": name, "state": "running"})
            running_assigned = True
            continue
        if state == "succeeded" or (stage_id == "database" and record.get("status") in {"installed", "installing", "failed"} and failed_at != "database"):
            view_state = "succeeded" if state == "succeeded" or stage_id == "database" else state
            if stage_id == "database" and state != "failed":
                view_state = "succeeded"
        elif stage_id == failed_at:
            view_state = "failed"
        elif record.get("status") == "installing" and not running_assigned:
            view_state = "running"
            running_assigned = True
        else:
            view_state = "pending"
        stages.append({"id": stage_id, "name": name, "state": view_state})
    return {
        "id": _installation_id(record),
        "sample": record.get("sample", ""),
        "version": record.get("version", ""),
        "startedAt": record.get("startedAt"),
        "finishedAt": record.get("finishedAt"),
        "installedAt": record.get("installedAt") if record.get("status") == "installed" else None,
        "status": _public_status(record),
        "requestedBy": actor_role,
        "stages": stages,
        "error": None
        if not error
        else {"code": error.get("code", "install_failed"), "stage": failed_at, "message": error.get("message", "")},
    }


def _card(item: dict, version: str, state: dict | None, actor_role: str, source_rejected: bool) -> dict:
    status = "unavailable" if source_rejected or item.get("status") == "unavailable" else _public_status(state or {})
    if state and state.get("error", {}).get("code") == "ownership_conflict":
        status = "conflict"
    installable = actor_role == "admin" and status in {"not_installed", "failed", "conflict"}
    installed = status == "installed"
    installed_version = str((state or {}).get("version") or "")
    return {
        "name": item.get("name"),
        "displayName": item.get("displayName") or item.get("name"),
        "summary": item.get("summary", ""),
        "version": version,
        "licenseNote": item.get("licenseNote", ""),
        "expectedTables": item.get("expectedTables", 0),
        "knowledgeNetwork": {
            "id": item.get("knowledgeNetworkId", ""),
            "displayName": item.get("knowledgeNetworkDisplayName") or item.get("knowledgeNetworkId", ""),
        },
        "components": dict(item.get("components") or {}),
        "installedVersion": installed_version if installed else "",
        "installedAt": (state or {}).get("installedAt") if installed else None,
        "manifestSha256": item.get("manifestSha256", ""),
        "versions": [{"version": version, "hasReleaseNotes": bool(item.get("releaseNotes"))}],
        "updateAvailable": installed and bool(installed_version) and installed_version != version,
        "questions": list(item.get("questions") or []),
        "status": status,
        "installable": installable,
        "installationId": _installation_id(state) if state else None,
        "message": (state or {}).get("error", {}).get("message", "") if state else item.get("code", ""),
    }


def _public_status(record: dict) -> str:
    status = record.get("status")
    if status in {"installing", "installed", "failed"}:
        if record.get("error", {}).get("code") == "ownership_conflict":
            return "conflict"
        return status
    return "not_installed"


def _failed_stage(record: dict) -> str:
    stages = record.get("stages") or {}
    if stages.get("database") == "failed":
        return "database"
    for stage_id, _name in STAGES:
        if stage_id == "database":
            continue
        if stages.get(stage_id) != "succeeded":
            return stage_id
    return "verify"


def _installation_id(record: dict | None) -> str:
    if not record:
        return ""
    return str(record.get("id") or f"inst-{record.get('sample', '')}")


def _read_state(state_dir: Path, sample: str) -> dict | None:
    path = state_dir / f"{sample}.json"
    if not sample or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_installing(state_dir: Path, sample: str, version: str, release_notes: dict | None = None,
                      manifest_sha256: str | None = None, data_image_ref: str | None = None) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "id": f"inst-{sample}",
        "sample": sample,
        "version": version,
        "status": "installing",
        "stages": {},
        "startedAt": timestamp(),
        "dataImageRef": data_image_ref,
        **({"releaseNotesSnapshot": release_notes} if release_notes else {}),
        **({"manifestSha256": manifest_sha256} if manifest_sha256 else {}),
    }
    write_json(state_dir / f"{sample}.json", record)


def _write_failed(state_dir: Path, sample: str, version: str, code: str, message: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    database_codes = {
        "database_not_ready",
        "image_unavailable",
        "sample_data_unavailable",
        "storage_class_missing",
    }
    current = _read_state(state_dir, sample) or {}
    record = {
        "id": f"inst-{sample}",
        "sample": sample,
        "version": version,
        "status": "failed",
        "stages": {"database": "failed"} if code in database_codes else {},
        "error": {"code": code, "message": message},
        "startedAt": current.get("startedAt"),
        "finishedAt": timestamp(),
        **({"releaseNotesSnapshot": current["releaseNotesSnapshot"]}
           if current.get("version") == version and current.get("releaseNotesSnapshot") else {}),
        **({"manifestSha256": current["manifestSha256"]}
           if current.get("version") == version and current.get("manifestSha256") else {}),
        **({"dataImageRef": current["dataImageRef"]}
           if current.get("version") == version and "dataImageRef" in current else {}),
        **({"remoteRelease": current["remoteRelease"]}
           if current.get("version") == version and current.get("remoteRelease") else {}),
    }
    write_json(state_dir / f"{sample}.json", record)


def _require_role(actor_role: str) -> None:
    if actor_role not in {"admin", "user"}:
        raise ApiError(401, "forbidden", "sign in to read the sample catalog")


def _require_sample(sample: str) -> None:
    if not NAME_RE.fullmatch(sample):
        raise ApiError(404, "install_failed", "unknown sample")


def _api_error(exc: ControlError) -> ApiError:
    status = 403 if exc.code == "forbidden" else 409 if exc.code in {"already_installed", "use_retry", "ownership_conflict"} else 500
    return ApiError(status, exc.code, exc.message)


def load_indexes(root: Path, image_index_path: Path) -> tuple[str, dict, dict]:
    version = read_version(root)
    repo_index = json.loads((root / "manifest-index.json").read_text(encoding="utf-8")) if (root / "manifest-index.json").is_file() else {"version": version, "sourceRepo": "https://github.com/openbkn-ai/bkn-samples", "samples": []}
    image_index = json.loads(image_index_path.read_text(encoding="utf-8"))
    return version, image_index, repo_index
