"""Catalog ownership and sample installation state. Does not call kubectl."""

from __future__ import annotations

import json
from pathlib import Path

OWNERSHIP_MANAGED_BY = "bkn-samples"
CATALOG_NAME = "bkn-sample-{sample}"


class ControlError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def catalog_name(sample: str) -> str:
    return CATALOG_NAME.format(sample=sample)


def ownership_tags(sample: str, version: str) -> list[str]:
    return [OWNERSHIP_MANAGED_BY, f"bkn-sample:{sample}", f"bkn-samples-version:{version}"]


def _state_path(state_dir: Path, sample: str) -> Path:
    return state_dir / f"{sample}.json"


def _read_state(state_dir: Path, sample: str) -> dict | None:
    path = _state_path(state_dir, sample)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(state_dir: Path, record: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    _state_path(state_dir, record["sample"]).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_admin(actor_role: str) -> None:
    if actor_role != "admin":
        raise ControlError("forbidden", "an administrator must install the sample")


def _catalogs_named(openbkn, name: str) -> list[dict]:
    payload = openbkn(["vega", "catalog", "list", "--name", name])
    if isinstance(payload, dict):
        entries = payload.get("entries") or []
    elif isinstance(payload, list):
        entries = payload
    else:
        entries = []
    return [entry for entry in entries if entry.get("name") == name]


def _owned(entry: dict, sample: str, version: str) -> bool:
    tags = set(entry.get("tags") or [])
    return set(ownership_tags(sample, version)).issubset(tags)


def ensure_catalog(sample: str, version: str, database: dict, openbkn) -> dict:
    name = catalog_name(sample)
    matches = _catalogs_named(openbkn, name)
    if matches:
        entry = matches[0]
        if not _owned(entry, sample, version):
            raise ControlError(
                "ownership_conflict",
                f"Catalog {name} already exists and is not managed by this installer",
            )
        if entry.get("database") not in (None, database["name"]):
            raise ControlError(
                "ownership_conflict",
                f"Catalog {name} points at a different database",
            )
        return entry
    created = openbkn(
        [
            "vega",
            "catalog",
            "create",
            "--name",
            name,
            "--connector-type",
            "mysql",
            "--connector-config",
            json.dumps(
                {
                    "host": database["host"],
                    "port": int(database["port"]),
                    "username": database["user"],
                    "database": database["name"],
                    "password": database["password"],
                },
                ensure_ascii=False,
            ),
            "--tags",
            ",".join(ownership_tags(sample, version)),
        ]
    )
    if not isinstance(created, dict) or not created.get("id"):
        raise ControlError("discover_incomplete", "catalog create did not return an id")
    return created


def _hook_input(sample: str, version: str, database: dict, catalog_id: str) -> dict:
    return {
        "apiVersion": "samples.openbkn.ai/v1alpha1",
        "sample": sample,
        "version": version,
        "database": database,
        "catalog": {"name": catalog_name(sample), "id": catalog_id},
        "knowledgeNetwork": {
            "id": "supply_ontology_hand",
            "displayName": "供应链本体知识网络-手工版",
        },
        "ownership": {
            "managedBy": OWNERSHIP_MANAGED_BY,
            "sample": sample,
            "version": version,
        },
    }


def _run_hook(hook_runner, payload: dict, stage: str) -> dict:
    result = hook_runner(stage, payload)
    if not isinstance(result, dict) or result.get("ok") is not True:
        message = (result or {}).get("message") if isinstance(result, dict) else "hook failed"
        code = "verify_failed" if stage == "platform-verify" else "install_failed"
        raise ControlError(code, message or "hook failed")
    return result


def create_installation(
    *,
    sample: str,
    version: str,
    actor_role: str,
    database: dict,
    state_dir: Path,
    openbkn,
    hook_runner,
) -> dict:
    _require_admin(actor_role)
    current = _read_state(state_dir, sample)
    if current and current.get("status") == "installed":
        raise ControlError("already_installed", f"{sample} is already installed")
    if current and current.get("status") == "failed":
        raise ControlError("use_retry", "retry the failed installation")
    return _advance(
        sample=sample,
        version=version,
        database=database,
        state_dir=state_dir,
        openbkn=openbkn,
        hook_runner=hook_runner,
        current=current,
    )


def retry_installation(
    *,
    sample: str,
    version: str,
    actor_role: str,
    database: dict,
    state_dir: Path,
    openbkn,
    hook_runner,
) -> dict:
    _require_admin(actor_role)
    current = _read_state(state_dir, sample)
    if not current or current.get("status") != "failed":
        raise ControlError("install_failed", "there is no failed installation to retry")
    return _advance(
        sample=sample,
        version=version,
        database=database,
        state_dir=state_dir,
        openbkn=openbkn,
        hook_runner=hook_runner,
        current=current,
    )


def _advance(*, sample, version, database, state_dir, openbkn, hook_runner, current) -> dict:
    record = current or {
        "sample": sample,
        "version": version,
        "status": "installing",
        "stages": {},
    }
    record["status"] = "installing"
    try:
        catalog = ensure_catalog(sample, version, database, openbkn)
        record["stages"]["discover"] = "succeeded"
        record["catalogId"] = catalog["id"]
        payload = _hook_input(sample, version, database, catalog["id"])
        if record["stages"].get("knowledge") != "succeeded":
            installed = _run_hook(hook_runner, payload, "platform-install")
            record["stages"]["knowledge"] = "succeeded"
            record["stages"]["capabilities"] = "succeeded"
            record["resources"] = installed.get("resources") or {}
        verified = _run_hook(hook_runner, payload, "platform-verify")
        record["stages"]["verify"] = "succeeded"
        record["checks"] = verified.get("checks") or []
        record["status"] = "installed"
    except ControlError as exc:
        record["status"] = "failed"
        record["error"] = {"code": exc.code, "message": exc.message}
        _write_state(state_dir, record)
        raise
    _write_state(state_dir, record)
    return record
