"""Studio catalog HTTP API. Auth is the caller's role; this module does not call kubectl."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from installer.control_plane import ControlError, create_installation, note_database_ready, retry_installation, timestamp
from installer.state_store import write_json
from installer.history import read_installation_history, record_terminal_installation
from installer.contract import read_version, sample_version
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
        _card(item, sample_version(item), _read_state(state_dir, item.get("name", "")), actor_role, merged["sourceRejected"])
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
        _write_failed(state_dir, sample, version, code, message, stage="database")
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
    records, complete = read_installation_history(state_dir, sample, record)
    return {"items": [installation_view(item, actor_role) for item in records],
            "historyComplete": complete}


def get_sample_release_notes(*, sample: str, version: str, actor_role: str,
                             pinned_version: str, image_index: dict, repo_index: dict,
                             state_dir: Path, locale: str = "zh-CN",
                             imported_release_notes: dict | None = None) -> dict:
    _require_role(actor_role)
    _require_sample(sample)
    record = _read_state(state_dir, sample)
    notes = (record or {}).get("releaseNotesSnapshot")
    if (not isinstance(notes, dict) or notes.get("version") != version) and isinstance(imported_release_notes, dict):
        if imported_release_notes.get("version") == version:
            notes = imported_release_notes
    if not isinstance(notes, dict) or notes.get("version") != version:
        merged = merge_catalog(pinned_version, image_index, repo_index)
        item = next((item for item in merged["samples"] if item.get("name") == sample), None)
        if merged["sourceRejected"] or not item or item.get("status") == "unavailable" or version != sample_version(item):
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


def get_sample_experience_set(*, knowledge_network: str, state_dir: Path, actor_role: str) -> dict:
    """The experience set of the installed sample that created this knowledge network.

    Only a successful installation that owns the network answers; any other network, including
    one with the same id made by hand, has no experience set.
    """
    _require_role(actor_role)
    for path in sorted(state_dir.glob("*.json")) if state_dir.is_dir() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (isinstance(record, dict) and record.get("status") == "installed"
                and (record.get("resources") or {}).get("knowledgeNetworkId") == knowledge_network
                and isinstance(record.get("experienceSet"), dict)):
            return {"sample": record.get("sample", path.stem), "version": record.get("version", ""),
                    "knowledgeNetwork": knowledge_network, "experienceSet": record["experienceSet"]}
    raise ApiError(404, "experience_set_unavailable", "this knowledge network has no sample experience set")


def installation_view(record: dict, actor_role: str) -> dict:
    error = record.get("error") if isinstance(record.get("error"), dict) else None
    download_failed = (record.get("status") == "failed" and record.get("operation") != "uninstall"
                       and (error or {}).get("code") == "release_download_failed")
    failed_at = _failed_stage(record) if record.get("status") in {"failed", "uninstall_failed"} and not download_failed else ""
    stages = []
    running_assigned = False
    from installer.uninstall import UNINSTALL_STAGES
    stage_names = UNINSTALL_STAGES if record.get("operation") == "uninstall" else STAGES
    for stage_id, name in stage_names:
        state = (record.get("stages") or {}).get(stage_id)
        if download_failed:
            stages.append({"id": stage_id, "name": name, "state": "pending"})
            continue
        if record.get("operation") == "uninstall":
            stages.append({"id": stage_id, "name": name, "state": state or "pending"})
            continue
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
        "attemptId": record.get("attemptId"),
        "sample": record.get("sample", ""),
        "version": record.get("version", ""),
        "startedAt": record.get("startedAt"),
        "finishedAt": record.get("finishedAt"),
        "installedAt": record.get("installedAt") if record.get("status") == "installed" else None,
        "status": _public_status(record),
        "requestedBy": actor_role,
        "operation": record.get("operation", "install"),
        "stages": stages,
        "error": None
        if not error
        else {"code": error.get("code", "install_failed"), "stage": failed_at, "message": error.get("message", "")},
    }


def _card(item: dict, version: str, state: dict | None, actor_role: str, source_rejected: bool) -> dict:
    status = _public_status(state or {})
    if state and state.get("operation") != "uninstall" and state.get("error", {}).get("code") == "ownership_conflict":
        status = "conflict"
    if status == "uninstalled":
        status = "not_installed"
    if status == "not_installed" and (source_rejected or item.get("status") == "unavailable"):
        status = "unavailable"
    installable = actor_role == "admin" and status in {"not_installed", "failed", "conflict"}
    installed = status == "installed"
    installed_version = str((state or {}).get("version") or "")
    receipt = (state or {}).get("resources", {}).get("ownedExecution")
    has_receipt = isinstance(receipt, dict) and all(isinstance(receipt.get(k), list) for k in ("toolboxes", "skills"))
    return {
        "name": item.get("name"),
        "displayName": item.get("displayName") or item.get("name"),
        "summary": item.get("summary", ""),
        "language": item.get("language"),
        "version": version,
        "licenseNote": item.get("licenseNote", ""),
        "expectedTables": item.get("expectedTables", 0),
        "knowledgeNetwork": {
            "id": item.get("knowledgeNetworkId", ""),
            "displayName": item.get("knowledgeNetworkDisplayName") or item.get("knowledgeNetworkId", ""),
        },
        "components": dict(item.get("components") or {}),
        "installedVersion": installed_version if installed or status in {"uninstalling", "uninstall_failed"} else "",
        "uninstallUnavailableReason": "ownership_receipt_missing" if installed and not has_receipt else "",
        "installedAt": (state or {}).get("installedAt") if installed else None,
        "manifestSha256": item.get("manifestSha256", ""),
        "versions": [{"version": version, "hasReleaseNotes": bool(item.get("releaseNotes"))}],
        "updateAvailable": installed and bool(installed_version) and installed_version != version,
        "questions": list(item.get("questions") or []),
        "status": status,
        "installable": installable,
        "canUninstall": actor_role == "admin" and (status in {"failed", "conflict", "uninstall_failed"}
            or (status == "installed" and has_receipt)),
        "installationId": _installation_id(state) if state else None,
        "message": (state or {}).get("error", {}).get("message", "") if state else item.get("code", ""),
    }


def _public_status(record: dict) -> str:
    status = record.get("status")
    if status in {"installing", "installed", "failed", "uninstalling", "uninstall_failed", "uninstalled"}:
        if record.get("operation") != "uninstall" and record.get("error", {}).get("code") == "ownership_conflict":
            return "conflict"
        return status
    return "not_installed"


def _failed_stage(record: dict) -> str:
    stages = record.get("stages") or {}
    if record.get("operation") == "uninstall":
        return next((name for name, value in stages.items() if value == "failed"), "")
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
    record_terminal_installation(state_dir, record)


def _write_failed(state_dir: Path, sample: str, version: str, code: str, message: str, *, stage: str | None = None) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    database_codes = {
        "database_not_ready",
        "image_unavailable",
        "offline_image_missing",
        "sample_data_unavailable",
        "storage_class_missing",
    }
    current = _read_state(state_dir, sample) or {}
    record = {
        "id": current.get("id") or f"inst-{sample}",
        "sample": sample,
        "version": version,
        "status": "failed",
        "stages": {stage: "failed"} if stage else ({"database": "failed"} if code in database_codes else {}),
        "error": {"code": code, "message": message},
        "startedAt": current.get("startedAt"),
        **({"attemptId": current["attemptId"]} if current.get("attemptId") else {}),
        **({"historyComplete": current["historyComplete"]} if "historyComplete" in current else {}),
        "finishedAt": timestamp(),
        **({"releaseNotesSnapshot": current["releaseNotesSnapshot"]}
           if current.get("version") == version and current.get("releaseNotesSnapshot") else {}),
        **({"manifestSha256": current["manifestSha256"]}
           if current.get("version") == version and current.get("manifestSha256") else {}),
        **({"dataImageRef": current["dataImageRef"]}
           if current.get("version") == version and "dataImageRef" in current else {}),
        **({"remoteRelease": current["remoteRelease"]}
           if current.get("version") == version and current.get("remoteRelease") else {}),
        **({"offlineRelease": current["offlineRelease"]}
           if current.get("version") == version and current.get("offlineRelease") else {}),
        **({"packageDigest": current["packageDigest"]}
           if current.get("version") == version and current.get("packageDigest") else {}),
        **({key: current[key] for key in ("catalogId", "resources", "databaseRuntime") if key in current}
           if current.get("version") == version else {}),
    }
    write_json(state_dir / f"{sample}.json", record)
    record_terminal_installation(state_dir, record)


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
