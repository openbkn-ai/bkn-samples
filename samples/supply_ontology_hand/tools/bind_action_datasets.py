"""Bind Action Dataset tables to KN object types through OpenBKN."""

import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import time
import yaml


_DISCOVERY_SUCCESS = {"completed"}
_DISCOVERY_FAILURE = {"failed", "cancelled", "stopped"}


def build_bindings(mapping: dict, *, kn_id: str, schema: str) -> list[dict]:
    result = []
    for item in mapping.get("bindings", []):
        dataset = str(item["dataset"])
        if dataset.startswith("${ACTION_DATASET_SCHEMA}."):
            dataset = f"{schema}.{dataset.split('.', 1)[1]}"
        elif "." not in dataset:
            dataset = f"{schema}.{dataset}"
        result.append({"kn_id": kn_id, "object_type_id": item["object_type_id"], "dataset": dataset})
    return result


def run_cmd(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout).strip())
    return proc.stdout


def parse_json(raw: str):
    data = json.loads(raw)
    if isinstance(data, dict) and isinstance(data.get("entries"), list):
        return data["entries"][0]
    return data


def find_resource_id(catalog_id: str, dataset: str, run_cmd=run_cmd) -> str:
    raw = run_cmd([
        "openbkn", "--json", "resource", "find",
        "--catalog-id", catalog_id, "--name", dataset, "--exact",
    ])
    data = json.loads(raw)
    entries = data.get("entries", []) if isinstance(data, dict) else data
    if isinstance(entries, dict):
        entries = [entries]
    for entry in entries or []:
        if entry.get("id"):
            return str(entry["id"])
    raise RuntimeError(f"resource not found for Action Dataset {dataset}")


def discover_catalog(catalog_id: str, run_cmd=run_cmd, *, timeout_seconds: float = 120) -> None:
    created = parse_json(run_cmd(["openbkn", "--json", "vega", "catalog", "discover", catalog_id]))
    task_id = created.get("id") if isinstance(created, dict) else None
    if not isinstance(task_id, str) or not task_id:
        raise RuntimeError(f"catalog discover returned no task id: {created!r}")

    deadline = time.monotonic() + timeout_seconds
    while True:
        task = parse_json(run_cmd(["openbkn", "--json", "vega", "discover-task", "get", task_id]))
        if not isinstance(task, dict):
            raise RuntimeError(f"discover task {task_id} returned unexpected payload: {task!r}")
        status = str(task.get("status", "")).lower()
        if status in _DISCOVERY_SUCCESS:
            return
        if status in _DISCOVERY_FAILURE:
            message = task.get("message")
            raise RuntimeError(f"discover task {task_id} {status}{': ' + str(message) if message else ''}")
        if time.monotonic() >= deadline:
            raise RuntimeError(f"discover task {task_id} did not complete within {timeout_seconds:g} seconds")
        time.sleep(2)


def resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == root.name:
        return root.parent / path
    return root / path


def run_bind(config: dict, mapping: dict, *, dry_run: bool, run_cmd=run_cmd) -> dict:
    kn_id = (config.get("openbkn") or {}).get("kn_id")
    if not kn_id:
        raise ValueError("openbkn.kn_id is required")
    schema = (config.get("database") or {}).get("schema") or "public"
    bindings = build_bindings(mapping, kn_id=kn_id, schema=schema)
    report = {"kn_id": kn_id, "dry_run": dry_run, "ok": True, "bindings": bindings}
    if dry_run:
        return report
    catalog_id = (config.get("vega") or {}).get("catalog_id")
    if not catalog_id:
        raise ValueError("vega.catalog_id is required for Action Dataset binding")
    for binding in bindings:
        resource_id = find_resource_id(catalog_id, binding["dataset"], run_cmd=run_cmd)
        binding["resource_id"] = resource_id
        ot_id = binding["object_type_id"]
        current = parse_json(run_cmd(["openbkn", "--json", "bkn", "object-type", "get", kn_id, ot_id]))
        body = copy.deepcopy(current)
        body["data_source"] = {"type": "resource", "id": resource_id}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(body, tmp, ensure_ascii=False)
            body_path = tmp.name
        try:
            run_cmd(["openbkn", "--json", "bkn", "object-type", "update", kn_id, ot_id, "--body-file", body_path])
        finally:
            Path(body_path).unlink(missing_ok=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", default="mapping/action_dataset_map.yaml")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    mapping = resolve_path(root, args.mapping)
    config = yaml.safe_load(resolve_path(root, args.config).read_text(encoding="utf-8"))
    payload = yaml.safe_load(mapping.read_text(encoding="utf-8"))
    report = run_bind(config, payload, dry_run=not args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
