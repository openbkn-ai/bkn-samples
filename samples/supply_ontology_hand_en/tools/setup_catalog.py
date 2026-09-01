"""Step 4: create Vega catalog, enable, discover tables, optionally write catalog_id to config."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import yaml

from bind_kn_resources import parse_cli_json

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_MAP = _SCRIPT_DIR / "mapping" / "object_table_map.yaml"
_UI_FALLBACK_MSG = "请按说明书步骤 4 UI 挂接扫描"
_DISCOVERY_SUCCESS = {"completed"}
_DISCOVERY_FAILURE = {"failed", "cancelled", "stopped"}


def run_cmd(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"openbkn failed ({proc.returncode}): {' '.join(args)}\n{detail}"
        )
    return proc.stdout


_default_run_cmd = run_cmd


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_mapping(path: Path | None = None) -> dict:
    map_path = path or _DEFAULT_MAP
    return yaml.safe_load(map_path.read_text(encoding="utf-8"))


def expected_tables(mapping: dict, table_prefix: str = "") -> list[str]:
    return [table_prefix + table for table in mapping["load_order"]]


def build_connector_config(cfg: dict) -> dict:
    db = cfg["database"]
    vega = cfg.get("vega") or {}
    host = vega.get("catalog_host") or db["host"]
    schema = db.get("schema") or "public"
    connector: dict[str, Any] = {
        "host": host,
        "port": int(db["port"]),
        "username": db["user"],
        "database": db["database"],
        "schemas": [schema] if isinstance(schema, str) else list(schema),
    }
    connector_options = vega.get("connector_options")
    if connector_options:
        connector["options"] = dict(connector_options)
    password = db.get("password")
    if password is None:
        password = ""
    connector["password"] = password
    return connector


def _catalog_list(*, run_cmd: Callable[[list[str]], str]) -> list[dict]:
    payload = parse_cli_json(run_cmd(["openbkn", "--json", "vega", "catalog", "list", "--limit", "-1"]))
    if isinstance(payload, dict):
        return list(payload.get("entries") or [])
    if isinstance(payload, list):
        return payload
    return []


def _find_catalog_by_name(name: str, *, run_cmd: Callable[[list[str]], str]) -> dict | None:
    for entry in _catalog_list(run_cmd=run_cmd):
        if entry.get("name") == name:
            return entry
    return None


def _single_catalog(payload: object, catalog_id: str) -> dict:
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        entries = payload["entries"]
        if len(entries) == 1 and isinstance(entries[0], dict):
            return entries[0]
    if isinstance(payload, dict):
        return payload
    raise RuntimeError(f"catalog get returned unexpected payload for {catalog_id}: {payload!r}")


def wait_for_discovery(
    catalog_id: str,
    *,
    run_cmd: Callable[[list[str]], str],
    timeout_seconds: float = 120,
    poll_interval_seconds: float = 2,
) -> dict:
    created = parse_cli_json(
        run_cmd(["openbkn", "--json", "vega", "catalog", "discover", catalog_id])
    )
    task_id = created.get("id") if isinstance(created, dict) else None
    if not isinstance(task_id, str) or not task_id:
        raise RuntimeError(f"catalog discover returned no task id: {created!r}")

    deadline = time.monotonic() + timeout_seconds
    while True:
        task = parse_cli_json(
            run_cmd(["openbkn", "--json", "vega", "discover-task", "get", task_id])
        )
        if not isinstance(task, dict):
            raise RuntimeError(f"discover task {task_id} returned unexpected payload: {task!r}")
        status = str(task.get("status", "")).lower()
        if status in _DISCOVERY_SUCCESS:
            return task
        if status in _DISCOVERY_FAILURE:
            message = task.get("message")
            raise RuntimeError(f"discover task {task_id} {status}{': ' + str(message) if message else ''}")
        if time.monotonic() >= deadline:
            raise RuntimeError(f"discover task {task_id} did not complete within {timeout_seconds:g} seconds")
        time.sleep(poll_interval_seconds)


def _catalog_resources(catalog_id: str, *, run_cmd: Callable[[list[str]], str]) -> list[dict]:
    payload = parse_cli_json(
        run_cmd(
            [
                "openbkn",
                "--json",
                "vega",
                "catalog",
                "resources",
                catalog_id,
                "--category",
                "table",
                "--limit",
                "-1",
            ]
        )
    )
    if isinstance(payload, dict):
        for key in ("entries", "resources", "items", "data"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return inner
    if isinstance(payload, list):
        return payload
    return []


def _resource_table_name(resource: dict) -> str | None:
    for key in ("table_name", "name"):
        value = resource.get(key)
        if not value:
            continue
        text = str(value)
        if "." in text:
            return text.rsplit(".", 1)[-1]
        return text
    return None


def verify_tables(
    catalog_id: str,
    mapping: dict,
    *,
    table_prefix: str = "",
    run_cmd: Callable[[list[str]], str],
) -> dict[str, Any]:
    expected = set(expected_tables(mapping, table_prefix))
    resources = _catalog_resources(catalog_id, run_cmd=run_cmd)
    found = {_resource_table_name(r) for r in resources}
    found.discard(None)
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    return {
        "expected_count": len(expected),
        "found_count": len(found & expected),
        "missing": missing,
        "extra_sample": extra[:10],
        "ok": not missing,
    }


def run_catalog_setup(
    config: dict,
    mapping: dict,
    *,
    dry_run: bool = False,
    rediscover: bool = False,
    skip_discover: bool = False,
    table_prefix: str = "",
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    vega = config.get("vega") or {}
    db = config["database"]
    catalog_name = vega.get("catalog_name") or f"supply-demo-{db['database']}"
    connector_type = vega.get("connector_type") or (
        "postgresql" if db["engine"] == "postgres" else db["engine"]
    )
    connector_config = build_connector_config(config)

    report: dict[str, Any] = {
        "catalog_name": catalog_name,
        "connector_type": connector_type,
        "connector_config_host": connector_config["host"],
        "database": db["database"],
        "dry_run": dry_run,
        "steps": [],
    }

    catalog_id = (vega.get("catalog_id") or "").strip()
    catalog_entry: dict | None = None
    if catalog_id:
        catalog_entry = _single_catalog(
            parse_cli_json(cmd(["openbkn", "--json", "vega", "catalog", "get", catalog_id])),
            catalog_id,
        )
        report["steps"].append({"action": "reuse_config_catalog_id", "catalog_id": catalog_id})
    else:
        catalog_entry = _find_catalog_by_name(catalog_name, run_cmd=cmd)
        if catalog_entry:
            catalog_id = catalog_entry["id"]
            report["steps"].append({"action": "reuse_existing_name", "catalog_id": catalog_id})
        elif dry_run:
            report["steps"].append({"action": "would_create", "catalog_name": catalog_name})
            report["verification"] = {"ok": False, "dry_run": True}
            return report
        else:
            create_args = [
                "openbkn",
                "--json",
                "vega",
                "catalog",
                "create",
                "--name",
                catalog_name,
                "--connector-type",
                connector_type,
                "--connector-config",
                json.dumps(connector_config, ensure_ascii=False),
                "--description",
                vega.get("catalog_description")
                or "Supply demo hand experience pack (auto setup)",
            ]
            catalog_entry = parse_cli_json(cmd(create_args))
            if not isinstance(catalog_entry, dict) or not catalog_entry.get("id"):
                raise RuntimeError(f"catalog create returned unexpected payload: {catalog_entry!r}")
            catalog_id = catalog_entry["id"]
            report["steps"].append({"action": "create", "catalog_id": catalog_id})

    report["catalog_id"] = catalog_id

    if dry_run:
        report["verification"] = verify_tables(catalog_id, mapping, table_prefix=table_prefix, run_cmd=cmd)
        return report

    if not catalog_entry.get("enabled"):
        cmd(["openbkn", "--json", "vega", "catalog", "enable", catalog_id])
        report["steps"].append({"action": "enable"})

    cmd(["openbkn", "--json", "vega", "catalog", "test-connection", catalog_id])
    report["steps"].append({"action": "test_connection"})

    if not skip_discover:
        task = wait_for_discovery(catalog_id, run_cmd=cmd)
        report["steps"].append({"action": "discover", "task_id": task.get("id")})
    else:
        report["steps"].append({"action": "discover_skipped"})

    verification = verify_tables(catalog_id, mapping, table_prefix=table_prefix, run_cmd=cmd)
    report["verification"] = verification
    if not verification["ok"]:
        missing = ", ".join(verification["missing"])
        raise RuntimeError(f"catalog scan missing expected tables: {missing}")

    return report


def write_catalog_id_to_config(config_path: Path, catalog_id: str) -> None:
    text = config_path.read_text(encoding="utf-8")
    if re.search(r"(?m)^(\s*)catalog_id:\s*.*$", text):
        updated = re.sub(
            r"(?m)^(\s*)catalog_id:\s*.*$",
            rf"\1catalog_id: {catalog_id!r}",
            text,
            count=1,
        )
    else:
        updated = text.rstrip() + f"\n  catalog_id: {catalog_id!r}\n"
    config_path.write_text(updated, encoding="utf-8")


def write_interactive_config(catalog_id: str, catalog_name: str, table_prefix: str) -> Path:
    """Write a credential-free config for later bind steps."""
    path = _SCRIPT_DIR / "config.poc.yaml"
    path.write_text(
        "openbkn:\n"
        "  kn_id: supply_ontology_hand_en\n"
        f"  kn_name: {catalog_name}\n"
        "vega:\n"
        f"  catalog_id: {catalog_id}\n"
        f"  catalog_name: {catalog_name}\n"
        "database:\n"
        "  schema: public\n"
        "load:\n"
        f"  table_prefix: {table_prefix}\n",
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Setup Vega catalog and discover sample tables (step 4)")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions; reuse catalog if configured")
    parser.add_argument("--rediscover", action="store_true", help="Alias for forcing discover (discover runs by default)")
    parser.add_argument(
        "--skip-discover",
        action="store_true",
        help="Skip discover (only enable + test-connection + verify existing resources)",
    )
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Write vega.catalog_id back into config file after success",
    )
    parser.add_argument("--interactive", action="store_true", help="Prompt for a new PostgreSQL connection and Catalog name")
    parser.add_argument("--table-prefix", default=None, help="Prefix on destination table names, e.g. hand_")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    try:
        if args.interactive:
            import getpass
            catalog_name = input("New Catalog name [Supply_Ontology_Hand_POC]: ").strip() or "Supply_Ontology_Hand_POC"
            host = input("PostgreSQL host: ").strip()
            port = int(input("Port [5432]: ") or "5432")
            database = input("Database name [supply_ontology_hand_poc]: ").strip() or "supply_ontology_hand_poc"
            user = input("Username: ").strip()
            password = getpass.getpass("Password (hidden): ")
            config = {"database": {"engine": "postgres", "host": host, "port": port, "database": database, "user": user, "password": password, "schema": "public"}, "vega": {"catalog_name": catalog_name, "catalog_host": host, "connector_type": "postgresql"}}
        else:
            config = load_config(config_path)
        mapping = load_mapping()
        table_prefix = args.table_prefix
        if table_prefix is None:
            table_prefix = (config.get("load") or {}).get("table_prefix", "")
        report = run_catalog_setup(
            config,
            mapping,
            dry_run=args.dry_run,
            rediscover=args.rediscover,
            skip_discover=args.skip_discover,
            table_prefix=table_prefix,
        )
        if args.write_config and report.get("catalog_id") and not args.dry_run:
            if args.interactive:
                path = write_interactive_config(report["catalog_id"], config["vega"]["catalog_name"], table_prefix)
                report["config_updated"] = str(path)
            else:
                write_catalog_id_to_config(config_path, report["catalog_id"])
                report["config_updated"] = str(config_path)

        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.dry_run:
            return 0
        if not (report.get("verification") or {}).get("ok"):
            return 1
        return 0
    except (RuntimeError, json.JSONDecodeError, OSError, yaml.YAMLError, KeyError) as exc:
        print(_UI_FALLBACK_MSG, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
