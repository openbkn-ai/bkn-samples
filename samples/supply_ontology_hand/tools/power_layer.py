"""Publish standard Object Metrics V1 and verify immutable queries and ownership."""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bind_kn_resources import (
    _object_type_from_get,
    load_config,
    parse_cli_json,
    run_cmd as _default_run_cmd,
)

_SCRIPT_DIR = Path(__file__).resolve().parent
_PAYLOAD_DIR = _SCRIPT_DIR / "assets"
_DEFAULT_METRICS = _PAYLOAD_DIR / "metrics-create.json"
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


def list_metrics_by_name(kn_id: str, *, run_cmd=None) -> dict[str, dict]:
    cmd = run_cmd or _default_run_cmd
    payload = json.loads(cmd(["openbkn", "--json", "bkn", "object-metric", "list", kn_id, "--limit", "500"]))
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        raise ValueError("Object metric list must contain entries")
    definitions = [record.get("definition") for record in payload["entries"]]
    if any(not isinstance(item, dict) or not item.get("name") for item in definitions):
        raise ValueError("Object metric list contains an invalid definition")
    names = [item["name"] for item in definitions]
    if len(names) != len(set(names)):
        raise ValueError("Object metric names must be unambiguous")
    return {item["name"]: item for item in definitions}


def metric_command(cmd, action, kn_id, *, definition=None, metric=None):
    command = ["openbkn", "--json", "bkn", "object-metric", action, kn_id]
    if metric is not None:
        command.extend([str(metric["id"]), "--metric-version", str(metric["version"])])
    if definition is None:
        return json.loads(cmd(command))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8") as body:
        json.dump(definition, body, ensure_ascii=False)
        body.flush()
        return json.loads(cmd(command + ["--body-file", body.name]))


def create_metrics(kn_id: str, entries: list[dict], *, dry_run=False, run_cmd=None) -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    existing = list_metrics_by_name(kn_id, run_cmd=cmd)
    report = {"kn_id": kn_id, "dry_run": dry_run, "created": [], "skipped": []}
    for definition in entries:
        name = definition["name"]
        metric = existing.get(name)
        if metric is not None:
            if (metric.get("owner_object_type_id") != definition["owner_object_type_id"]
                    or metric.get("code") != definition["code"]
                    or metric.get("version") != definition["version"]):
                raise RuntimeError(f"Existing object metric does not match sample definition: {name}")
            # A published immutable version must never silently reuse a different definition.
            for key in ("metric_type", "calculation_scope", "result_semantics", "specification", "query_capabilities"):
                if metric.get(key) != definition.get(key):
                    raise RuntimeError(f"Existing object metric {name} differs at {key}")
        if dry_run:
            report.setdefault("would_create", []).append(name)
            continue
        if metric is None:
            record = metric_command(cmd, "create", kn_id, definition=definition)
            metric = record.get("definition") if isinstance(record, dict) else None
            if not isinstance(metric, dict) or not metric.get("id") or metric.get("version") != definition["version"]:
                raise RuntimeError(f"Object metric draft creation failed: {name}")
        if metric.get("lifecycle", {}).get("status") != "published":
            validated = metric_command(cmd, "validate-saved", kn_id, metric=metric)
            candidate = validated.get("definition") if isinstance(validated, dict) else None
            if not isinstance(candidate, dict) or candidate.get("lifecycle", {}).get("status") != "validated":
                raise RuntimeError(f"Object metric validation failed: {name}: {validated}")
            published = metric_command(cmd, "publish", kn_id, metric=metric)
            metric = published.get("definition") if isinstance(published, dict) else None
            if not isinstance(metric, dict) or metric.get("lifecycle", {}).get("status") != "published":
                raise RuntimeError(f"Object metric publication failed: {name}")
            report["created"].append({"name": name, "id": metric["id"], "version": metric["version"]})
        else:
            report["skipped"].append(name)
    return report


def verify_metric_ownership(kn_id: str, entries: list[dict], *, run_cmd=None) -> dict[str, Any]:
    """Object-set aggregates belong to object types; they are not instance properties."""
    cmd = run_cmd or _default_run_cmd
    metrics = list_metrics_by_name(kn_id, run_cmd=cmd)
    report = {"kn_id": kn_id, "passed": [], "failed": []}
    for spec in entries:
        metric = metrics.get(spec["name"], {})
        owner = spec["owner_object_type_id"]
        obj = _object_type_from_get(parse_cli_json(cmd(
            ["openbkn", "--json", "bkn", "object-type", "get", kn_id, owner])), owner)
        ok = (metric.get("owner_object_type_id") == owner and obj.get("id") == owner
              and metric.get("code") == spec["code"] and metric.get("version") == spec["version"]
              and metric.get("calculation_scope") == "object_set"
              and metric.get("lifecycle", {}).get("status") == "published")
        row = {"metric_name": spec["name"], "metric_id": metric.get("id"),
               "version": metric.get("version"), "owner_object_type_id": owner}
        if not ok:
            row["error"] = "Published object metric version or owner object type mismatch"
        report["passed" if ok else "failed"].append(row)
    return report


def query_metric(cmd, kn_id, metric, body):
    if not metric.get("id") or not isinstance(metric.get("version"), int):
        raise ValueError("Object metric ID and explicit version are required")
    if metric.get("lifecycle", {}).get("status") != "published":
        raise ValueError("Only published object metrics can be queried")
    payload = json.loads(cmd(["openbkn", "--json", "bkn", "object-metric", "query", kn_id,
                                 str(metric["id"]), "--metric-version", str(metric["version"]),
                                 "--body", json.dumps(body, ensure_ascii=False)]))
    if (not isinstance(payload, dict) or payload.get("status") != "ok"
            or payload.get("model", {}).get("version") != metric["version"]
            or payload.get("model", {}).get("metric_id") != metric["id"]):
        raise ValueError("Object metric query did not return the requested successful immutable version")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Object metric query returned no entries")
    series = []
    for entry in entries:
        value = entry.get("value")
        if (entry.get("status") != "ok" or isinstance(value, bool)
                or not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError("Object metric query returned an unavailable or non-numeric value")
        item = {"labels": entry.get("dimensions") or {}, "values": [value]}
        if "time" in entry and entry["time"] is not None:
            item["times"] = [entry["time"]]
        series.append(item)
    return series, payload


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


def values_close(actual: Any, expected: Any, rel_tol: float = 1e-9) -> bool:
    try:
        actual_n = float(actual)
        expected_n = float(expected)
    except (TypeError, ValueError):
        return actual == expected
    return math.isclose(actual_n, expected_n, rel_tol=rel_tol, abs_tol=1e-9)


def metric_series_match(datas: Any, expected: list[dict], business_timezone: str = "UTC") -> bool:
    """Verify every label and bucket, independent of series ordering."""
    if not isinstance(datas, list) or len(datas) != len(expected):
        return False
    remaining = list(datas)
    for want in expected:
        matches = [item for item in remaining if isinstance(item, dict)
                   and (item.get("labels") or {}) == want.get("labels", {})]
        if len(matches) != 1:
            return False
        item = matches[0]
        remaining.remove(item)
        for key in ("values", "proportions", "growth_values", "growth_rates"):
            if key in want:
                actual = item.get(key)
                if not isinstance(actual, list) or len(actual) != len(want[key]):
                    return False
                if not all(values_close(a, b) for a, b in zip(actual, want[key])):
                    return False
        if "periods" in want:
            periods = item.get("time_strs") or item.get("times") or []
            try:
                zone = ZoneInfo(business_timezone)
                actual_periods = []
                for value in periods:
                    if isinstance(value, (int, float)):
                        moment = datetime.fromtimestamp(float(value) / 1000, zone)
                    elif isinstance(value, str) and "T" in value:
                        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        if moment.tzinfo is not None:
                            moment = moment.astimezone(zone)
                    else:
                        actual_periods.append(str(value)[:7])
                        continue
                    actual_periods.append(moment.strftime("%Y-%m"))
            except (ValueError, TypeError, OverflowError, OSError, ZoneInfoNotFoundError):
                return False
            if actual_periods != want["periods"]:
                return False
    return True


def calendar_month_growth(metric: dict, kn_id: str, case: dict, zone_name: str, cmd) -> tuple[list, list]:
    """Query complete consecutive calendar months and retain each native V1 response."""
    zone = ZoneInfo(zone_name)
    queries = case.get("queries") or []
    if len(queries) < 2:
        raise ValueError("Calendar month comparison requires a baseline month")
    periods, totals, evidence = [], [], []
    previous_end = None
    for query in queries:
        period = query["period"]
        year, month = map(int, period.split("-"))
        start = datetime(year, month, 1, tzinfo=zone)
        end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=zone)
        if previous_end is not None and start != previous_end:
            raise ValueError("Comparison months must be consecutive")
        previous_end = end
        owner = metric["owner_object_type_id"]
        expected = {"node_type": "group", "boolean_operator": "and", "children": [
            {"node_type": "predicate", "left": {"source": "property", "property_ref": {
                "object_type_id": owner, "property_name": "signing_date"}},
             "comparison_operator": op, "right": [{"source": "literal", "value_type": "date", "value": value}]}
            for op, value in (("gte", start.date().isoformat()), ("lt", end.date().isoformat()))
        ]}
        if query["body"] != {"filter": expected}:
            raise ValueError(f"{period}: expected explicit complete calendar month boundaries")
        series, payload = query_metric(cmd, kn_id, metric, query["body"])
        if len(series) != 1 or series[0]["labels"] or len(series[0]["values"]) != 1:
            raise ValueError(f"{period}: missing or ambiguous monthly total")
        total = series[0]["values"][0]
        evidence.append({"period": period, "body": query["body"], "response": payload})
        periods.append(period)
        totals.append(total)
    if case.get("calculation") == "calendar_month_series":
        return [{"labels": {}, "time_strs": periods, "values": totals}], evidence
    return [{"labels": {}, "time_strs": periods[1:], "values": totals[1:],
             "growth_values": [b-a for a, b in zip(totals, totals[1:])]}], evidence


def verify_metrics(kn_id: str, cases: list[dict], *, run_cmd=None, business_timezone="UTC") -> dict[str, Any]:
    cmd = run_cmd or _default_run_cmd
    metrics = list_metrics_by_name(kn_id, run_cmd=cmd)
    report = {"kn_id": kn_id, "passed": [], "failed": []}
    for case in cases:
        metric = metrics.get(case["metric_name"])
        row = {"id": case.get("id"), "metric_name": case["metric_name"]}
        try:
            if metric is None:
                raise ValueError("Object metric not found")
            row.update(metric_id=metric["id"], version=metric["version"])
            if case.get("calculation") in ("calendar_month_growth", "calendar_month_series"):
                actual, evidence = calendar_month_growth(metric, kn_id, case, business_timezone, cmd)
                totals = [item["response"]["entries"][0]["value"] for item in evidence]
                expected_totals = case.get("expected_monthly_totals")
                if (not isinstance(expected_totals, list) or len(totals) != len(expected_totals)
                        or not all(values_close(a, b) for a, b in zip(totals, expected_totals))):
                    raise ValueError("Monthly source totals mismatch")
                row["queries"] = evidence
                row["calculation_location"] = "acceptance client arithmetic over native Object Metrics V1 results"
            else:
                actual, response = query_metric(cmd, kn_id, metric, case.get("body") or {})
                row["response"] = response
                if case.get("calculation") == "proportion":
                    total = sum(item["values"][0] for item in actual)
                    if total == 0:
                        raise ValueError("Proportion denominator is zero")
                    for item in actual:
                        item["proportions"] = [item["values"][0] / total * 100]
                        if case.get("period"):
                            item["time_strs"] = [case["period"]]
                    row["calculation_location"] = "acceptance client arithmetic over native grouped values"
            if "expected_series" in case:
                expected = case["expected_series"]
                matched = metric_series_match(actual, expected, business_timezone)
                row.update(actual=actual, expected=expected)
            else:
                expected = case.get("expected_value")
                value = metric_query_scalar(actual)
                matched = (len(actual) == 1 and not actual[0]["labels"] and expected is not None
                           and values_close(value, expected))
                row.update(actual=value, expected=expected)
            if not matched:
                raise ValueError("Object metric value or series mismatch")
            report["passed"].append(row)
        except (ValueError, TypeError, KeyError, ZoneInfoNotFoundError) as exc:
            row["error"] = str(exc)
            report["failed"].append(row)
    return report


def _load_optional_config(path: str | None) -> dict | None:
    if not path:
        return None
    return load_config(Path(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish Object Metrics V1 and verify queries and ownership"
    )
    parser.add_argument(
        "command",
        choices=["create", "verify-ownership", "verify", "all"],
        help="publish metrics / verify ownership / verify queries / all",
    )
    parser.add_argument("--config", help="Path to tools/config.yaml (optional)")
    parser.add_argument("--kn-id", help="Knowledge network id (default: config or supply_ontology_hand)")
    parser.add_argument("--metrics-file", default=str(_DEFAULT_METRICS))
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

        if args.command == "verify-ownership":
            reports["verify_metric_ownership"] = verify_metric_ownership(
                kn_id, extract_metric_entries(load_json(Path(args.metrics_file)))
            )

        if args.command in ("verify", "all") and not args.dry_run:
            query_payload = load_json(Path(args.query_file))
            cases = query_payload.get("cases") if isinstance(query_payload, dict) else query_payload
            if not isinstance(cases, list):
                raise ValueError("metrics-query-examples.json must contain cases[]")
            reports["verify_metrics"] = verify_metrics(
                kn_id, cases,
                business_timezone=(query_payload.get("business_timezone", "UTC")
                                   if isinstance(query_payload, dict) else "UTC"),
            )
            reports["verify_metric_ownership"] = verify_metric_ownership(
                kn_id, extract_metric_entries(load_json(Path(args.metrics_file))))
            failed = (
                reports["verify_metrics"]["failed"]
                + reports["verify_metric_ownership"]["failed"]
            )
            print(json.dumps(reports, ensure_ascii=False, indent=2))
            return 1 if failed else 0

        print(json.dumps(reports, ensure_ascii=False, indent=2))
        return 1 if reports.get("verify_metric_ownership", {}).get("failed") else 0
    except (RuntimeError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(_UI_FALLBACK_MSG, file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
