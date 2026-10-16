"""Object Metrics V1 publication, immutable query, and sample ownership contract."""
import copy
import json
from pathlib import Path

import pytest

from power_layer import (create_metrics, extract_metric_entries, list_metrics_by_name,
                         metric_query_scalar, query_metric, verify_metric_ownership,
                         verify_metrics)

PACK = Path(__file__).resolve().parents[2]
ASSETS = PACK / "tools/assets"
DEFINITIONS = json.loads((ASSETS / "metrics-create.json").read_text())["entries"]


def record(definition=None, status="published"):
    metric = copy.deepcopy(definition or DEFINITIONS[0])
    metric.update(id="metric-1")
    metric["lifecycle"]["status"] = status
    return {"definition": metric}


def response(metric=None, values=None, status="ok"):
    metric = metric or record()["definition"]
    return {"model": {"metric_id": metric["id"], "version": metric["version"]},
            "entries": values if values is not None else [{"value": 30, "status": "ok"}], "status": status}


def test_source_definitions_are_eleven_standard_object_set_metrics():
    assert len(DEFINITIONS) == 11
    assert len({m["code"] for m in DEFINITIONS}) == 11
    for m in DEFINITIONS:
        assert m["version"] == 1
        assert m["calculation_scope"] == "object_set"
        assert m["lifecycle"]["status"] == "draft"
        assert m["owner_object_type_id"]
        assert "scope_ref" not in m and "calculation_formula" not in m
        assert "logic_property" not in m
        assert "business_qualifiers" not in m["specification"]
    assert DEFINITIONS[5]["result_semantics"]["value"]["physical_type"] == "decimal"
    assert DEFINITIONS[6]["result_semantics"]["value"]["physical_type"] == "decimal"
    assert DEFINITIONS[9]["result_semantics"]["value"]["physical_type"] == "decimal"


def test_empty_definition_payload_rejected():
    with pytest.raises(ValueError):
        extract_metric_entries({"entries": []})


def test_publication_is_draft_validate_then_publish_with_explicit_version():
    actions = []
    def run(args):
        action = args[4]
        actions.append(action)
        if action == "list":
            return json.dumps({"entries": [], "total_count": 0})
        if action == "create":
            body = json.loads(Path(args[-1]).read_text())
            assert body == DEFINITIONS[0]
            return json.dumps(record(status="draft"))
        assert args[args.index("--metric-version") + 1] == "1"
        return json.dumps(record(status="validated" if action == "validate-saved" else "published"))
    report = create_metrics("network", [DEFINITIONS[0]], run_cmd=run)
    assert actions == ["list", "create", "validate-saved", "publish"]
    assert report["created"][0]["version"] == 1


def test_failed_validation_never_publishes():
    actions = []
    def run(args):
        action = args[4]
        actions.append(action)
        if action == "list": return json.dumps({"entries": []})
        if action == "create": return json.dumps(record(status="draft"))
        return json.dumps({"issues": [{"code": "invalid"}]})
    with pytest.raises(RuntimeError, match="validation failed"):
        create_metrics("network", [DEFINITIONS[0]], run_cmd=run)
    assert "publish" not in actions


def test_published_metric_cannot_silently_reuse_a_changed_definition():
    existing = record()
    existing["definition"]["specification"]["measure"]["aggregation"] = "sum"
    with pytest.raises(RuntimeError, match="differs"):
        create_metrics("network", [DEFINITIONS[0]], run_cmd=lambda _: json.dumps({"entries": [existing]}))


def test_list_requires_v1_records_and_unique_names():
    for payload in ({"entries": [DEFINITIONS[0]]}, {"entries": [record(), record()]}, []):
        with pytest.raises(ValueError):
            list_metrics_by_name("network", run_cmd=lambda _: json.dumps(payload))


def test_query_requires_successful_nonempty_exact_version_response():
    metric = record()["definition"]
    for payload in (response(values=[]), response(values=[{"status": "no_data"}]),
                    response(values=[{"status": "ok", "value": True}]), response(status="partial")):
        with pytest.raises(ValueError):
            query_metric(lambda _: json.dumps(payload), "network", metric, {})
    wrong = response(); wrong["model"]["version"] = 2
    with pytest.raises(ValueError):
        query_metric(lambda _: json.dumps(wrong), "network", metric, {})
    calls = []
    def run(args):
        calls.append(args)
        return json.dumps(response())
    series, _ = query_metric(run, "network", metric, {})
    assert metric_query_scalar(series) == 30
    assert calls[0][calls[0].index("--metric-version") + 1] == "1"


def test_ownership_checks_published_version_and_actual_owner_without_mutation():
    calls = []
    def run(args):
        calls.append(args)
        if args[3] == "object-metric": return json.dumps({"entries": [record()]})
        return json.dumps({"entries": [{"id": DEFINITIONS[0]["owner_object_type_id"]}]})
    report = verify_metric_ownership("network", [DEFINITIONS[0]], run_cmd=run)
    assert report["passed"] and not report["failed"]
    assert not any("update" in args for args in calls)
    altered = copy.deepcopy(DEFINITIONS[0]); altered["version"] = 2
    assert verify_metric_ownership("network", [altered], run_cmd=run)["failed"]


def test_scalar_does_not_accept_grouped_or_empty_results_as_summary():
    metric = record()["definition"]
    def run(args):
        if args[4] == "list": return json.dumps({"entries": [{"definition": metric}]})
        return json.dumps(response(values=[{"dimensions": {"attr": "A"}, "value": 30, "status": "ok"}]))
    assert verify_metrics("network", [{"metric_name": metric["name"], "expected_value": 30}], run_cmd=run)["failed"]
