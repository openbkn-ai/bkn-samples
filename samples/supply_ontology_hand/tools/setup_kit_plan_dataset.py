#!/usr/bin/env python3
"""Create the kit-schedule plan dataset, bind its object type and load the installed plan history.

The plan object is written by the kit-schedule Function, so it is backed by a Vega dataset in the
sample's own catalog rather than by a database table. The dataset schema follows the object type in
``kn/``; the history rows come from ``data/kit_schedule_plan.csv``. Re-running is idempotent: an
existing dataset with the same name in the catalog is reused and history rows are rewritten by plan ID.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

try:
    from installer.sample_logging import run as run_sample_command
except ImportError:
    run_sample_command = subprocess.run

from bind_kn_resources import _object_type_from_get, _sanitize_ot_for_bind_update, parse_cli_json

SAMPLE_DIR = Path(__file__).resolve().parents[1]
OBJECT_SUFFIX = "_kitplan"
DATASET_NAME = "kit_schedule_plan"
VEGA = "/api/vega-backend/v1"


def run_cmd(args: list[str]) -> str:
    proc = run_sample_command(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"openbkn failed ({proc.returncode}): {(proc.stderr or proc.stdout or '').strip()}")
    return proc.stdout


def plan_object(kn_id: str) -> dict[str, Any]:
    network = json.loads(next((SAMPLE_DIR / "kn").glob("*.json")).read_text(encoding="utf-8"))
    return next(item for item in network["object_types"] if item["id"] == kn_id + OBJECT_SUFFIX)


def dataset_schema(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"name": p["mapped_field"]["name"], "display_name": p["display_name"], "type": p["mapped_field"]["type"],
             "description": p.get("comment") or ""} for p in plan["data_properties"]]


def history_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    types = {p["mapped_field"]["name"]: p["mapped_field"]["type"] for p in plan["data_properties"]}
    rows = []
    with (SAMPLE_DIR / "data" / f"{DATASET_NAME}.csv").open(encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = {}
            for key, value in raw.items():
                if value in ("", None):
                    continue
                if types[key] == "integer":
                    row[key] = int(value)
                elif types[key] == "decimal":
                    number = float(value)
                    row[key] = int(number) if number.is_integer() else number
                else:
                    row[key] = value
            rows.append(row)
    return rows


def _entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("entries", "data", "resources"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return payload if isinstance(payload, list) else []


def run(config: dict, *, cmd: Callable[[list[str]], str] = run_cmd) -> dict[str, Any]:
    kn_id = config["openbkn"]["kn_id"]
    catalog_id = config["vega"]["catalog_id"]
    plan = plan_object(kn_id)

    def call(path: str, method: str = "GET", body: Any = None) -> Any:
        args = ["openbkn", "--json", "call", path, "-X", method]
        if body is not None:
            args += ["-d", json.dumps(body, ensure_ascii=False)]
        output = cmd(args).strip()
        return json.loads(output) if output else {}

    listed = _entries(parse_cli_json(cmd(["openbkn", "--json", "vega", "catalog", "resources", catalog_id,
                                          "--category", "dataset", "--limit", "-1"])))
    existing = next((r for r in listed if r.get("name") == DATASET_NAME), None)
    if existing is None:
        created = call(f"{VEGA}/resources", "POST", {"catalog_id": catalog_id, "name": DATASET_NAME, "category": "dataset",
                                                     "description": plan["comment"], "schema_definition": dataset_schema(plan)})
        resource_id = created["id"]
    else:
        resource_id = existing["id"]

    ot_body = _object_type_from_get(parse_cli_json(cmd(["openbkn", "--json", "bkn", "object-type", "get", kn_id, plan["id"]])), plan["id"])
    update = _sanitize_ot_for_bind_update(ot_body)
    update["data_source"] = {"type": "resource", "id": resource_id}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(update, tmp, ensure_ascii=False)
        body_file = tmp.name
    try:
        cmd(["openbkn", "--json", "bkn", "object-type", "update", kn_id, plan["id"], "--body-file", body_file])
    finally:
        Path(body_file).unlink(missing_ok=True)

    rows = history_rows(plan)
    for row in rows:
        call(f"{VEGA}/resources/{resource_id}/data/{row['plan_id']}", "PUT", row)
    return {"resource_id": resource_id, "created": existing is None, "object_type_id": plan["id"], "history_rows": len(rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    print(json.dumps(run(config), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
