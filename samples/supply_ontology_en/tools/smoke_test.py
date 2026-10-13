"""Smoke test: KN existence, bound OT row counts, and DB join hit rates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

import yaml
from sqlalchemy import text
from sqlalchemy.engine import Engine

from bind_kn_resources import load_mapping, parse_cli_json, run_cmd as _default_run_cmd
from load_sample_data import build_engine, quote_ident

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_REPORT = _SCRIPT_DIR / "smoke_report.json"
_DEFAULT_MAP = _SCRIPT_DIR / "mapping" / "object_table_map.yaml"

# Hit rate definition: among distinct non-null, non-empty left_key values in
# left_table, the fraction that also appear as right_key values in right_table.
HIT_RATE_DEFINITION = (
    "distinct non-null non-empty left keys that exist in right key set / "
    "distinct non-null non-empty left keys"
)


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def join_hit_rate(
    left_keys: list[Any],
    right_keys: list[Any],
) -> tuple[float, int, int]:
    """Return (hit_rate, hit_count, left_distinct_count)."""
    left_set = {
        str(k).strip()
        for k in left_keys
        if k is not None and str(k).strip() != ""
    }
    right_set = {
        str(k).strip()
        for k in right_keys
        if k is not None and str(k).strip() != ""
    }
    if not left_set:
        return 0.0, 0, 0
    hits = sum(1 for key in left_set if key in right_set)
    return hits / len(left_set), hits, len(left_set)


def _fetch_column_values(
    engine: Engine,
    table: str,
    column: str,
    engine_name: str,
) -> list[Any]:
    q_table = quote_ident(table, engine_name)
    q_col = quote_ident(column, engine_name)
    sql = f"SELECT {q_col} FROM {q_table}"
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    return [row[0] for row in rows]


def compute_join_hit_rate(
    engine: Engine,
    check: dict,
    engine_name: str,
) -> dict[str, Any]:
    left_values = _fetch_column_values(
        engine, check["left_table"], check["left_key"], engine_name
    )
    right_values = _fetch_column_values(
        engine, check["right_table"], check["right_key"], engine_name
    )
    hit_rate, hit_count, left_count = join_hit_rate(left_values, right_values)
    expect = float(check.get("expect_hit_rate", 1.0))
    return {
        "name": check["name"],
        "left_table": check["left_table"],
        "left_key": check["left_key"],
        "right_table": check["right_table"],
        "right_key": check["right_key"],
        "expect_hit_rate": expect,
        "hit_rate": hit_rate,
        "hit_count": hit_count,
        "left_key_count": left_count,
        "passed": hit_rate >= expect,
        "definition": HIT_RATE_DEFINITION,
    }


def run_join_checks(
    engine: Engine,
    mapping: dict,
    engine_name: str,
) -> list[dict[str, Any]]:
    return [
        compute_join_hit_rate(engine, check, engine_name)
        for check in mapping.get("join_checks", [])
    ]


def parse_query_rows(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("datas", "items", "rows", "data", "results", "instances", "entries"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return len(inner)
        for key in ("total", "count", "total_count"):
            if key in payload:
                return int(payload[key])
    return 0


def check_kn(
    config: dict,
    *,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    openbkn = config.get("openbkn") or {}
    kn_id = openbkn.get("kn_id")
    expected_name = openbkn.get("kn_name")
    if not kn_id:
        raise RuntimeError("openbkn.kn_id is required in config")
    if not expected_name:
        raise RuntimeError("openbkn.kn_name is required in config")

    raw = cmd(["openbkn", "--json", "bkn", "get", kn_id])
    payload = parse_cli_json(raw)
    actual_name = payload.get("name") if isinstance(payload, dict) else None
    passed = actual_name == expected_name
    return {
        "kn_id": kn_id,
        "expected_name": expected_name,
        "actual_name": actual_name,
        "passed": passed,
    }


def check_object_types(
    config: dict,
    mapping: dict,
    *,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> list[dict[str, Any]]:
    cmd = run_cmd or _default_run_cmd
    kn_id = (config.get("openbkn") or {}).get("kn_id")
    if not kn_id:
        raise RuntimeError("openbkn.kn_id is required in config")

    results: list[dict[str, Any]] = []
    for obj in mapping.get("objects", []):
        ot_id = obj["object_type_id"]
        if obj.get("bind") is False:
            results.append(
                {
                    "object_type_id": ot_id,
                    "skipped": True,
                    "reason": "bind:false",
                    "passed": True,
                }
            )
            continue

        query_args = [
            "openbkn",
            "--json",
            "bkn",
            "object-type",
            "query",
            kn_id,
            ot_id,
            "--body",
            '{"limit":1}',
        ]
        raw = cmd(query_args)
        payload = parse_cli_json(raw)
        row_count = parse_query_rows(payload)
        passed = row_count > 0
        results.append(
            {
                "object_type_id": ot_id,
                "table": obj.get("table"),
                "row_count": row_count,
                "skipped": False,
                "passed": passed,
            }
        )
    return results


def run_smoke(
    config: dict,
    mapping: dict,
    *,
    engine: Engine | None = None,
    run_cmd: Callable[[list[str]], str] | None = None,
    report_path: Path | None = None,
) -> tuple[bool, dict[str, Any]]:
    engine_name = (config.get("database") or {}).get("engine", "postgres")
    db_engine = engine or build_engine(config["database"])

    kn_check = check_kn(config, run_cmd=run_cmd)
    ot_checks = check_object_types(config, mapping, run_cmd=run_cmd)
    join_results = run_join_checks(db_engine, mapping, engine_name)

    passed = (
        kn_check["passed"]
        and all(row["passed"] for row in ot_checks)
        and all(row["passed"] for row in join_results)
    )

    report: dict[str, Any] = {
        "passed": passed,
        "kn_check": kn_check,
        "object_type_checks": ot_checks,
        "join_checks": join_results,
        "hit_rate_definition": HIT_RATE_DEFINITION,
    }

    out_path = report_path or _DEFAULT_REPORT
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return passed, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test KN binding and sample DB joins")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument(
        "--report",
        default=str(_DEFAULT_REPORT),
        help="Path to write smoke_report.json",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(Path(args.config))
        mapping = load_mapping(_DEFAULT_MAP)
        passed, report = run_smoke(
            config,
            mapping,
            report_path=Path(args.report),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if passed else 1
    except (RuntimeError, json.JSONDecodeError, OSError, yaml.YAMLError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
