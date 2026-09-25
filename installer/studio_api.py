"""Studio catalog HTTP API. Auth is the caller's role; this module does not call kubectl."""

from __future__ import annotations

import json
import re
from pathlib import Path

from installer.control_plane import ControlError, create_installation, retry_installation
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
    try:
        deploy(sample)
    except Exception as exc:
        code = getattr(exc, "code", "database_not_ready")
        message = getattr(exc, "message", str(exc))
        _write_failed(state_dir, sample, version, code, message)
        raise ApiError(409 if code in {"already_installed", "use_retry"} else 500, code, message) from exc
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


def installation_view(record: dict, actor_role: str) -> dict:
    error = record.get("error") if isinstance(record.get("error"), dict) else None
    failed_at = _failed_stage(record) if record.get("status") == "failed" else ""
    stages = []
    running_assigned = False
    for stage_id, name in STAGES:
        state = (record.get("stages") or {}).get(stage_id)
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
    installable = actor_role == "admin" and status in {"not_installed", "failed"}
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
        "updateAvailable": installed and bool(installed_version) and installed_version != version,
        "questions": list(item.get("questions") or []) if installed else [],
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


def _write_failed(state_dir: Path, sample: str, version: str, code: str, message: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "id": f"inst-{sample}",
        "sample": sample,
        "version": version,
        "status": "failed",
        "stages": {},
        "error": {"code": code, "message": message},
    }
    (state_dir / f"{sample}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
