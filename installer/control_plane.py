"""Catalog ownership and sample installation state. Does not call kubectl."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from installer.state_store import write_json

OWNERSHIP_MANAGED_BY = "bkn-samples"
CATALOG_NAME = "bkn-sample-{sample}"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ControlError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def catalog_name(sample: str) -> str:
    return CATALOG_NAME.format(sample=sample)


def ownership_tags(sample: str, version: str) -> list[str]:
    """Tags Vega will accept. ':' and '.' are rejected by the catalog API."""
    return [
        OWNERSHIP_MANAGED_BY,
        f"bkn-sample-{sample}",
        "bkn-samples-version-" + version.replace(".", "-"),
    ]


def _state_path(state_dir: Path, sample: str) -> Path:
    return state_dir / f"{sample}.json"


def _read_state(state_dir: Path, sample: str) -> dict | None:
    path = _state_path(state_dir, sample)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(state_dir: Path, record: dict) -> None:
    write_json(_state_path(state_dir, record["sample"]), record)


def _checkpoint(state_dir: Path, record: dict, **stage_updates: str) -> None:
    """Persist the in-progress record so a refresh can show the finished steps."""
    record["status"] = "installing"
    record.pop("error", None)
    stages = record.setdefault("stages", {})
    for name, state in stage_updates.items():
        if state == "running" and stages.get(name) == "succeeded":
            continue
        stages[name] = state
    _write_state(state_dir, record)


def note_database_ready(state_dir: Path, sample: str, version: str) -> None:
    """Record that the sample database is ready and discovery is the current step."""
    current = _read_state(state_dir, sample) or {
        "id": f"inst-{sample}",
        "sample": sample,
        "version": version,
        "status": "installing",
        "stages": {},
        "startedAt": timestamp(),
    }
    current["sample"] = sample
    current["version"] = version
    current.setdefault("id", f"inst-{sample}")
    _checkpoint(state_dir, current, database="succeeded", discover="running")


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


def _table_count(payload) -> int:
    """Count discovered business tables. The installer metadata table is not one of them."""
    count = 0
    for entry in _payload_entries(payload):
        name = str(entry.get("name") or "")
        if name.rsplit(".", 1)[-1] == "bkn_sample_meta":
            continue
        count += 1
    return count


def _payload_entries(payload) -> list:
    if isinstance(payload, dict):
        for key in ("entries", "resources", "items", "data"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return inner
    if isinstance(payload, list):
        return payload
    return []


def scan_catalog(catalog: dict, expected_tables: int, openbkn, attempts: int = 30, sleep=None) -> None:
    """Enable the catalog, test it, and wait until discovery returns the declared table count."""
    pause = time.sleep if sleep is None else sleep
    catalog_id = catalog["id"]
    openbkn(["vega", "catalog", "enable", catalog_id])
    openbkn(["vega", "catalog", "test-connection", catalog_id])
    openbkn(["vega", "catalog", "discover", catalog_id])
    found = 0
    for _ in range(attempts):
        resources = openbkn(
            ["vega", "catalog", "resources", catalog_id, "--category", "table", "--limit", "-1"]
        )
        found = _table_count(resources)
        if found == expected_tables:
            return
        pause(2)
    raise ControlError(
        "discover_incomplete",
        f"discovered {found} tables, expected {expected_tables}",
    )


def _hook_input(sample: str, version: str, database: dict, catalog_id: str, knowledge_network: dict, components: dict | None = None) -> dict:
    return {
        "apiVersion": "samples.openbkn.ai/v1alpha1",
        "sample": sample,
        "version": version,
        "database": database,
        "catalog": {"name": catalog_name(sample), "id": catalog_id},
        "knowledgeNetwork": {
            "id": knowledge_network["id"],
            "displayName": knowledge_network["displayName"],
        },
        "components": dict(components or {}),
        "ownership": {
            "managedBy": OWNERSHIP_MANAGED_BY,
            "sample": sample,
            "version": version,
        },
    }


def _run_hook(hook_runner, payload: dict, stage: str) -> dict:
    result = hook_runner(stage, payload)
    if isinstance(result, dict) and result.get("code") == "ownership_conflict":
        raise ControlError(
            "ownership_conflict",
            result.get("message") or "published capabilities do not match the installation record",
        )
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
    expected_tables: int,
    knowledge_network: dict,
    components: dict | None = None,
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
        expected_tables=expected_tables,
        knowledge_network=knowledge_network,
        components=components,
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
    expected_tables: int,
    knowledge_network: dict,
    components: dict | None = None,
    accepted: bool = False,
) -> dict:
    _require_admin(actor_role)
    current = _read_state(state_dir, sample)
    if not current or current.get("status") != ("installing" if accepted else "failed"):
        raise ControlError("install_failed", "there is no failed installation to retry")
    if current.get("version") != version:
        raise ControlError("version_changed", "retry requires the original installed artifacts")
    return _advance(
        sample=sample,
        version=version,
        database=database,
        state_dir=state_dir,
        openbkn=openbkn,
        hook_runner=hook_runner,
        current=current,
        expected_tables=expected_tables,
        knowledge_network=knowledge_network,
        components=components,
    )


def _advance(*, sample, version, database, state_dir, openbkn, hook_runner, current, expected_tables, knowledge_network, components=None) -> dict:
    record = current or {
        "id": f"inst-{sample}",
        "sample": sample,
        "version": version,
        "status": "installing",
        "stages": {},
        "startedAt": timestamp(),
    }
    record.setdefault("id", f"inst-{sample}")
    record.setdefault("stages", {})
    record.pop("finishedAt", None)
    _checkpoint(state_dir, record, database="succeeded", discover="running")
    try:
        catalog = ensure_catalog(sample, version, database, openbkn)
        scan_catalog(catalog, expected_tables, openbkn)
        record["catalogId"] = catalog["id"]
        _checkpoint(state_dir, record, discover="succeeded", knowledge="running")
        payload = _hook_input(sample, version, database, catalog["id"], knowledge_network, components)
        if record["stages"].get("knowledge") != "succeeded" or record["stages"].get("capabilities") != "succeeded":
            if record.get("capabilitySummary"):
                payload = {**payload, "capabilitySummary": record["capabilitySummary"]}
            installed = _run_hook(hook_runner, payload, "platform-install")
            reported = (installed.get("resources") or {}).get("capabilitySummary")
            previous = record.get("capabilitySummary")
            if previous and reported != previous:
                raise ControlError(
                    "ownership_conflict",
                    "published capabilities do not match the installation record",
                )
            record["resources"] = installed.get("resources") or {}
            if reported:
                record["capabilitySummary"] = reported
            _checkpoint(state_dir, record, knowledge="succeeded", capabilities="succeeded")
        _checkpoint(state_dir, record, verify="running")
        verified = _run_hook(hook_runner, payload, "platform-verify")
        record["checks"] = verified.get("checks") or []
        record["stages"]["verify"] = "succeeded"
        record["status"] = "installed"
        record["installedAt"] = timestamp()
        record["finishedAt"] = record["installedAt"]
    except ControlError as exc:
        record["status"] = "failed"
        record["finishedAt"] = timestamp()
        record["error"] = {"code": exc.code, "message": exc.message}
        _write_state(state_dir, record)
        raise
    _write_state(state_dir, record)
    return record
