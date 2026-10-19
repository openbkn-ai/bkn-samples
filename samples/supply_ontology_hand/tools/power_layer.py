"""Step 8: create metrics, bind them as object logic properties, verify snapshots."""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from bind_kn_resources import (
    _object_type_from_get,
    _sanitize_ot_for_bind_update,
    load_config,
    parse_cli_json,
    run_cmd as _default_run_cmd,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
_PAYLOAD_DIR = _SCRIPT_DIR / "assets"
_DEFAULT_METRICS = _PAYLOAD_DIR / "metrics-create.json"
_DEFAULT_LP = _PAYLOAD_DIR / "logic-properties.json"
_DEFAULT_QUERY = _PAYLOAD_DIR / "metrics-query-examples.json"
_DEFAULT_KN = "supply_ontology_hand"
_UI_FALLBACK_MSG = "请按 docs/openbkn-hand-import-guide_cn.md 检查 OpenBKN 认证与知识网络 ID"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_metric_entries(payload: Any) -> list[dict]:
    """Accept wrapper {entries:[...]} or a bare list of metric defs."""
    if isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict):
        entries = payload.get("entries")
    else:
        raise ValueError("metrics payload must be a list or an object with entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("metrics payload entries is empty")
    for item in entries:
        if not isinstance(item, dict) or not item.get("name"):
            raise ValueError("each metric entry must have a name")
    return entries


def resolve_kn_id(config: dict | None, kn_id: str | None) -> str:
    if kn_id:
        return kn_id
    if config:
        found = (config.get("openbkn") or {}).get("kn_id")
        if found:
            return str(found)
    return _DEFAULT_KN


def list_metrics_by_name(
    kn_id: str,
    *,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict[str, dict]:
    cmd = run_cmd or _default_run_cmd
    payload = parse_cli_json(
        cmd(["openbkn", "--json", "bkn", "metric", "list", kn_id])
    )
    entries = []
    if isinstance(payload, dict):
        entries = payload.get("entries") or []
    elif isinstance(payload, list):
        entries = payload
    by_name: dict[str, dict] = {}
    for item in entries or []:
        if isinstance(item, dict) and item.get("name"):
            by_name[str(item["name"])] = item
    return by_name


def create_metrics(
    kn_id: str,
    entries: list[dict],
    *,
    dry_run: bool = False,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    existing = list_metrics_by_name(kn_id, run_cmd=cmd)
    to_create = [e for e in entries if e["name"] not in existing]
    report: dict[str, Any] = {
        "kn_id": kn_id,
        "dry_run": dry_run,
        "existing": [
            {"name": name, "id": existing[name].get("id")} for name in existing
        ],
        "created": [],
        "skipped": [e["name"] for e in entries if e["name"] in existing],
    }
    if dry_run:
        report["would_create"] = [e["name"] for e in to_create]
        return report
    if not to_create:
        return report

    body = {"entries": to_create}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(body, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        raw = cmd(
            [
                "openbkn",
                "--json",
                "bkn",
                "metric",
                "create",
                kn_id,
                "--body-file",
                tmp_path,
            ]
        )
        try:
            created_payload = json.loads(raw) if raw.strip() else []
        except json.JSONDecodeError:
            created_payload = raw
        report["create_response"] = created_payload
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    after = list_metrics_by_name(kn_id, run_cmd=cmd)
    for entry in to_create:
        found = after.get(entry["name"])
        if not found or not found.get("id"):
            raise RuntimeError(f"metric create did not return {entry['name']}")
        if found.get("scope_ref") != entry.get("scope_ref"):
            raise RuntimeError(
                f"metric {entry['name']} scope_ref mismatch: "
                f"{found.get('scope_ref')} != {entry.get('scope_ref')}"
            )
        report["created"].append({"name": entry["name"], "id": found["id"]})
    return report


def strip_system_parameters(lp: dict) -> dict:
    cleaned = copy.deepcopy(lp)
    params = [
        p
        for p in (cleaned.get("parameters") or [])
        if isinstance(p, dict) and not p.get("if_system_generate")
    ]
    cleaned["parameters"] = params
    return cleaned


def build_logic_property(spec: dict, metric_id: str) -> dict:
    return {
        "name": spec["name"],
        "display_name": spec.get("display_name") or spec["name"],
        "type": spec.get("type") or "metric",
        "comment": spec.get("comment") or "",
        "data_source": {"type": "metric", "id": metric_id},
        "parameters": copy.deepcopy(spec.get("parameters") or []),
    }


def merge_logic_properties(existing: list | None, incoming: list[dict]) -> list[dict]:
    by_name: dict[str, dict] = {}
    for lp in existing or []:
        if not isinstance(lp, dict) or not lp.get("name"):
            continue
        by_name[str(lp["name"])] = strip_system_parameters(lp)
    for lp in incoming:
        by_name[str(lp["name"])] = lp
    return list(by_name.values())


def bind_logic_properties(
    kn_id: str,
    bindings: list[dict],
    *,
    dry_run: bool = False,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    metrics = list_metrics_by_name(kn_id, run_cmd=cmd)
    report: dict[str, Any] = {
        "kn_id": kn_id,
        "dry_run": dry_run,
        "bound": [],
        "missing_metrics": [],
    }

    for group in bindings:
        ot_id = group["object_type_id"]
        incoming: list[dict] = []
        for spec in group.get("logic_properties") or []:
            metric_name = spec.get("metric_name") or spec.get("display_name")
            metric = metrics.get(metric_name)
            if not metric or not metric.get("id"):
                report["missing_metrics"].append(
                    {"object_type_id": ot_id, "metric_name": metric_name}
                )
                continue
            if metric.get("scope_ref") != ot_id:
                raise RuntimeError(
                    f"cannot bind {metric_name} onto {ot_id}: "
                    f"metric.scope_ref={metric.get('scope_ref')}"
                )
            incoming.append(build_logic_property(spec, str(metric["id"])))
            report["bound"].append(
                {
                    "object_type_id": ot_id,
                    "logic_property": spec["name"],
                    "metric_name": metric_name,
                    "metric_id": metric["id"],
                }
            )

        if dry_run or not incoming:
            continue

        ot_body = _object_type_from_get(
            parse_cli_json(
                cmd(["openbkn", "--json", "bkn", "object-type", "get", kn_id, ot_id])
            ),
            ot_id,
        )
        data_prop_names = {
            p.get("name")
            for p in (ot_body.get("data_properties") or [])
            if isinstance(p, dict) and p.get("name")
        }
        clashes = [lp["name"] for lp in incoming if lp["name"] in data_prop_names]
        if clashes:
            raise RuntimeError(
                f"{ot_id}: logic property name clashes with data property: "
                + ", ".join(clashes)
            )
        update_body = _sanitize_ot_for_bind_update(ot_body)
        update_body["logic_properties"] = merge_logic_properties(
            update_body.get("logic_properties"), incoming
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(update_body, tmp, ensure_ascii=False)
            tmp_path = tmp.name
        try:
            cmd(
                [
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
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    if report["missing_metrics"]:
        names = ", ".join(m["metric_name"] for m in report["missing_metrics"])
        raise RuntimeError(f"metrics not found, create them first: {names}")
    return report


def metric_query_scalar(datas: Any) -> float | int | None:
    if not isinstance(datas, list) or not datas:
        return None
    first = datas[0]
    if not isinstance(first, dict):
        return None
    values = first.get("values")
    if not isinstance(values, list) or not values:
        return None
    return values[0]


def values_close(actual: Any, expected: Any, rel_tol: float = 0.02) -> bool:
    try:
        actual_n = float(actual)
        expected_n = float(expected)
    except (TypeError, ValueError):
        return actual == expected
    if expected_n == 0:
        return actual_n == 0
    return abs(actual_n - expected_n) / abs(expected_n) <= rel_tol


def verify_metrics(
    kn_id: str,
    cases: list[dict],
    *,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    metrics = list_metrics_by_name(kn_id, run_cmd=cmd)
    report: dict[str, Any] = {"kn_id": kn_id, "passed": [], "failed": []}

    for case in cases:
        name = case["metric_name"]
        metric = metrics.get(name)
        if not metric or not metric.get("id"):
            report["failed"].append(
                {"id": case.get("id"), "metric_name": name, "error": "metric not found"}
            )
            continue
        body = case.get("body") or {}
        raw = cmd(
            [
                "openbkn",
                "--json",
                "bkn",
                "metric",
                "query",
                kn_id,
                str(metric["id"]),
                "--body",
                json.dumps(body, ensure_ascii=False),
            ]
        )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            report["failed"].append(
                {
                    "id": case.get("id"),
                    "metric_name": name,
                    "error": f"invalid query response: {raw[:300]}",
                }
            )
            continue
        actual = metric_query_scalar(payload.get("datas"))
        expected = case.get("expected_value")
        row = {
            "id": case.get("id"),
            "metric_name": name,
            "metric_id": metric["id"],
            "title": case.get("title"),
            "actual": actual,
            "expected": expected,
        }
        if expected is None or values_close(actual, expected):
            report["passed"].append(row)
        else:
            row["error"] = "value mismatch"
            report["failed"].append(row)
    return report


def verify_logic_properties(
    kn_id: str,
    bindings: list[dict],
    *,
    run_cmd: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    metrics = list_metrics_by_name(kn_id, run_cmd=cmd)
    report: dict[str, Any] = {"kn_id": kn_id, "passed": [], "failed": []}

    for group in bindings:
        ot_id = group["object_type_id"]
        ot = _object_type_from_get(
            parse_cli_json(
                cmd(["openbkn", "--json", "bkn", "object-type", "get", kn_id, ot_id])
            ),
            ot_id,
        )
        existing = {
            lp.get("name"): lp
            for lp in (ot.get("logic_properties") or [])
            if isinstance(lp, dict)
        }
        for spec in group.get("logic_properties") or []:
            lp = existing.get(spec["name"])
            metric = metrics.get(spec.get("metric_name") or spec.get("display_name"))
            ds = (lp or {}).get("data_source") or {}
            ok = (
                isinstance(lp, dict)
                and lp.get("type") == "metric"
                and ds.get("type") == "metric"
                and metric
                and ds.get("id") == metric.get("id")
            )
            row = {
                "object_type_id": ot_id,
                "logic_property": spec["name"],
                "metric_name": spec.get("metric_name"),
                "metric_id": (metric or {}).get("id"),
                "bound_id": ds.get("id"),
            }
            if ok:
                report["passed"].append(row)
            else:
                row["error"] = "logic property missing or metric id mismatch"
                report["failed"].append(row)
    return report


def _load_optional_config(path: str | None) -> dict | None:
    if not path:
        return None
    return load_config(Path(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create metrics, bind logic properties, verify snapshots (step 8)"
    )
    parser.add_argument(
        "command",
        choices=["create", "bind", "verify", "all"],
        help="create metrics / bind logic properties / verify / all",
    )
    parser.add_argument("--config", help="Path to tools/config.yaml (optional)")
    parser.add_argument("--kn-id", help="Knowledge network id (default: config or supply_ontology_hand)")
    parser.add_argument("--metrics-file", default=str(_DEFAULT_METRICS))
    parser.add_argument("--logic-file", default=str(_DEFAULT_LP))
    parser.add_argument("--query-file", default=str(_DEFAULT_QUERY))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = _load_optional_config(args.config)
        kn_id = resolve_kn_id(config, args.kn_id)
        reports: dict[str, Any] = {"kn_id": kn_id, "command": args.command}

        if args.command in ("create", "all"):
            entries = extract_metric_entries(load_json(Path(args.metrics_file)))
            reports["create"] = create_metrics(
                kn_id, entries, dry_run=args.dry_run
            )

        if args.command in ("bind", "all"):
            lp_payload = load_json(Path(args.logic_file))
            bindings = lp_payload.get("bindings") if isinstance(lp_payload, dict) else lp_payload
            if not isinstance(bindings, list):
                raise ValueError("logic-properties.json must contain bindings[]")
            reports["bind"] = bind_logic_properties(
                kn_id, bindings, dry_run=args.dry_run
            )

        if args.command in ("verify", "all") and not args.dry_run:
            query_payload = load_json(Path(args.query_file))
            cases = query_payload.get("cases") if isinstance(query_payload, dict) else query_payload
            if not isinstance(cases, list):
                raise ValueError("metrics-query-examples.json must contain cases[]")
            lp_payload = load_json(Path(args.logic_file))
            bindings = lp_payload.get("bindings") if isinstance(lp_payload, dict) else lp_payload
            reports["verify_metrics"] = verify_metrics(kn_id, cases)
            reports["verify_logic_properties"] = verify_logic_properties(kn_id, bindings)
            failed = (
                reports["verify_metrics"]["failed"]
                + reports["verify_logic_properties"]["failed"]
            )
            print(json.dumps(reports, ensure_ascii=False, indent=2))
            return 1 if failed else 0

        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(_UI_FALLBACK_MSG, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
