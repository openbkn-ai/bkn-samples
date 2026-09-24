"""Bind knowledge-network object types to Vega catalog resources via openbkn CLI."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_MAP = _SCRIPT_DIR / "mapping" / "object_table_map.yaml"
_UI_FALLBACK_MSG = "请按说明书步骤 5 UI 手绑"


def parse_cli_json(raw: str) -> Any:
    """Parse openbkn --json stdout; unwrap common envelope keys."""
    data = json.loads(raw)
    if isinstance(data, dict):
        for key in ("data", "items", "resources", "entries", "result"):
            inner = data.get(key)
            if inner is not None:
                return inner
    return data


def _bare_table_name(identifier: str) -> str:
    text = str(identifier).strip()
    if "." in text:
        return text.rsplit(".", 1)[-1]
    return text


def match_resource_id(resources: list[dict], table: str) -> str | None:
    """Return resource id when name/table_name/source_identifier matches table (schema-aware)."""
    target = table.strip()
    for res in resources:
        resource_id = res.get("id")
        if not resource_id:
            continue
        for key in ("table_name", "name", "source_identifier"):
            value = res.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text == target or _bare_table_name(text) == target:
                return resource_id
    return None


def _resource_name_candidates(table: str, schema: str | None) -> list[str]:
    candidates = [table]
    if schema:
        qualified = f"{schema}.{table}"
        if qualified not in candidates:
            candidates.append(qualified)
    return candidates


def run_cmd(args: list[str]) -> str:
    """Run a subprocess command; raise RuntimeError on nonzero exit."""
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"openbkn failed ({proc.returncode}): {' '.join(args)}\n{detail}"
        )
    return proc.stdout


_default_run_cmd = run_cmd


def _resource_list_from_payload(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    return []


def _object_type_from_get(payload: Any, ot_id: str) -> dict:
    """Normalize object-type get JSON (often {\"entries\": [ot]}) to a single OT dict."""
    if isinstance(payload, dict) and "entries" in payload:
        entries = payload.get("entries")
        if not isinstance(entries, list) or not entries:
            raise RuntimeError(f"object-type get returned no entries for {ot_id}")
        for entry in entries:
            if isinstance(entry, dict) and entry.get("id") == ot_id:
                return entry
        first = entries[0]
        if isinstance(first, dict):
            return first
        raise RuntimeError(f"object-type get returned invalid entries for {ot_id}")
    if isinstance(payload, list):
        if not payload:
            raise RuntimeError(f"object-type get returned empty list for {ot_id}")
        first = payload[0]
        if isinstance(first, dict):
            return first
        raise RuntimeError(f"object-type get returned invalid list for {ot_id}")
    if isinstance(payload, dict):
        return payload
    raise RuntimeError(f"unexpected object-type get payload for {ot_id}")


def _sanitize_ot_for_bind_update(ot_body: dict, *, preserve_vector_config: bool = False) -> dict:
    """Strip env-specific vector model ids so bind update does not fail cross-environment."""
    body = copy.deepcopy(ot_body)
    for prop_key in ("data_properties", "logic_properties"):
        props = body.get(prop_key)
        if not isinstance(props, list):
            continue
        for prop in props:
            if not isinstance(prop, dict):
                continue
            index_config = prop.get("index_config")
            if not isinstance(index_config, dict):
                continue
            vector_config = index_config.get("vector_config")
            if (
                not preserve_vector_config
                and isinstance(vector_config, dict)
                and vector_config.get("model_id")
            ):
                vector_config["model_id"] = ""
                vector_config["enabled"] = False
    return body


def find_resource_id(
    catalog_id: str,
    table: str,
    *,
    schema: str | None = "public",
    run_cmd: Callable[[list[str]], str] | None = None,
) -> str | None:
    """Find catalog resource by table; tries bare name and schema-qualified name."""
    cmd = run_cmd or _default_run_cmd
    for name in _resource_name_candidates(table, schema):
        find_args = [
            "openbkn",
            "--json",
            "resource",
            "find",
            "--catalog-id",
            catalog_id,
            "--name",
            name,
            "--exact",
        ]
        found = _resource_list_from_payload(parse_cli_json(cmd(find_args)))
        resource_id = match_resource_id(found, table)
        if resource_id:
            return resource_id

    list_args = [
        "openbkn",
        "--json",
        "resource",
        "list",
        "--catalog-id",
        catalog_id,
        "--limit",
        "-1",
    ]
    listed = _resource_list_from_payload(parse_cli_json(cmd(list_args)))
    resource_id = match_resource_id(listed, table)
    if resource_id:
        return resource_id

    catalog_resources_args = [
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
    catalog_listed = _resource_list_from_payload(parse_cli_json(cmd(catalog_resources_args)))
    return match_resource_id(catalog_listed, table)


def run_bind(
    config: dict,
    mapping: dict,
    *,
    dry_run: bool = False,
    table_prefix: str = "",
    preserve_vector_config: bool = False,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict:
    """Bind OTs with bind:true to catalog resources; return execution report."""
    cmd = run_cmd or _default_run_cmd
    catalog_id = (config.get("vega") or {}).get("catalog_id") or ""
    if not catalog_id:
        raise RuntimeError("vega.catalog_id is empty; fill it after step 4 UI scan")

    kn_id = (config.get("openbkn") or {}).get("kn_id")
    if not kn_id:
        raise RuntimeError("openbkn.kn_id is required in config")

    report: dict[str, Any] = {
        "kn_id": kn_id,
        "catalog_id": catalog_id,
        "dry_run": dry_run,
        "bound": [],
        "skipped": [],
    }

    schema = (config.get("database") or {}).get("schema") or "public"

    for obj in mapping.get("objects", []):
        ot_id = obj["object_type_id"]
        if obj.get("bind") is False:
            report["skipped"].append({"object_type_id": ot_id, "reason": "bind:false"})
            continue

        table = table_prefix + obj["table"]
        resource_id = find_resource_id(catalog_id, table, schema=schema, run_cmd=cmd)
        if not resource_id:
            raise RuntimeError(f"resource not found for table {table!r} (OT {ot_id})")

        entry = {
            "object_type_id": ot_id,
            "table": table,
            "resource_id": resource_id,
        }
        report["bound"].append(entry)

        if dry_run:
            continue

        get_args = ["openbkn", "--json", "bkn", "object-type", "get", kn_id, ot_id]
        ot_body = _object_type_from_get(parse_cli_json(cmd(get_args)), ot_id)
        if not ot_body.get("name"):
            raise RuntimeError(f"object-type get missing name for {ot_id}")

        update_body = _sanitize_ot_for_bind_update(
            ot_body, preserve_vector_config=preserve_vector_config
        )
        update_body["data_source"] = {"type": "resource", "id": resource_id}

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            json.dump(update_body, tmp, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            update_args = [
                "openbkn",
                "--json",
                "bkn",
                "object-type",
                "update",
                kn_id,
                ot_id,
                "--body-file",
                tmp_path,
            ]
            cmd(update_args)
        finally:
            try:
                Path(tmp_path).unlink()
            except FileNotFoundError:
                pass

    return report


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_mapping(path: Path | None = None) -> dict:
    map_path = path or _DEFAULT_MAP
    return yaml.safe_load(map_path.read_text(encoding="utf-8"))


def print_dry_run_lines(report: dict) -> None:
    for row in report["bound"]:
        print(
            f"{row['object_type_id']}\t{row['table']}\t{row['resource_id']}",
            flush=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind KN object types to catalog resources")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Print OT→table→resource_id only")
    parser.add_argument("--mapping", default=str(_DEFAULT_MAP), help="Path to OT→table mapping YAML")
    parser.add_argument("--table-prefix", default=None, help="Prefix on destination table names, e.g. hand_")
    parser.add_argument(
        "--preserve-vector-config",
        action="store_true",
        help="Keep vector model IDs already normalized for this target environment",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config))
        mapping = load_mapping(Path(args.mapping))
        dry_run = args.dry_run or bool((config.get("bind") or {}).get("dry_run"))
        table_prefix = args.table_prefix
        if table_prefix is None:
            table_prefix = (config.get("load") or {}).get("table_prefix", "")
        report = run_bind(
            config,
            mapping,
            dry_run=dry_run,
            table_prefix=table_prefix,
            preserve_vector_config=args.preserve_vector_config,
        )
        if dry_run:
            print_dry_run_lines(report)
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, json.JSONDecodeError, OSError, yaml.YAMLError) as exc:
        print(_UI_FALLBACK_MSG, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
