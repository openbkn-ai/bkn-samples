"""Unit tests for power_layer helpers and payload consistency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from power_layer import (
    build_logic_property,
    extract_metric_entries,
    merge_logic_properties,
    metric_query_scalar,
    metric_series_match,
    strip_system_parameters,
    values_close,
)

PACK = Path(__file__).resolve().parents[2]
PAYLOADS = PACK / "tools" / "assets"
METRICS_FILE = PAYLOADS / "metrics-create.json"
LP_FILE = PAYLOADS / "logic-properties.json"
QUERY_FILE = PAYLOADS / "metrics-query-examples.json"


def test_extract_entries_from_wrapper():
    entries = extract_metric_entries(
        {"comment": "x", "entries": [{"name": 'Product Count', "scope_ref": "ot"}]}
    )
    assert entries[0]["name"] == 'Product Count'


def test_extract_entries_from_list():
    entries = extract_metric_entries([{"name": 'Material Count'}])
    assert entries[0]["name"] == 'Material Count'


def test_extract_entries_rejects_empty():
    with pytest.raises(ValueError):
        extract_metric_entries({"entries": []})


def test_strip_system_parameters():
    lp = {
        "name": "product_total_count",
        "parameters": [
            {"name": "instant", "if_system_generate": True},
            {"name": "materialattr", "value_from": "input"},
        ],
    }
    cleaned = strip_system_parameters(lp)
    assert [p["name"] for p in cleaned["parameters"]] == ["materialattr"]
    assert lp["parameters"][0]["name"] == "instant"


def test_merge_logic_properties_replaces_by_name():
    existing = [
        {"name": "keep_me", "type": "operator", "parameters": []},
        {
            "name": "product_total_count",
            "type": "metric",
            "data_source": {"type": "metric", "id": "old"},
            "parameters": [{"name": "instant", "if_system_generate": True}],
        },
    ]
    incoming = [
        build_logic_property(
            {
                "name": "product_total_count",
                "display_name": 'Product Count',
                "comment": "new",
                "parameters": [],
            },
            "new-id",
        )
    ]
    merged = merge_logic_properties(existing, incoming)
    by_name = {lp["name"]: lp for lp in merged}
    assert by_name["keep_me"]["type"] == "operator"
    assert by_name["product_total_count"]["data_source"]["id"] == "new-id"
    assert by_name["product_total_count"]["parameters"] == []


def test_metric_query_scalar_and_tolerance():
    assert metric_query_scalar([{"labels": {}, "values": [534]}]) == 534
    assert metric_query_scalar([]) is None
    assert values_close(534, 534)
    assert not values_close(540, 534)
    assert not values_close(91, 90)
    assert values_close(534.00000001, 534)
    assert not values_close(600, 534)


def test_pack_payloads_exist_and_align():
    metrics = extract_metric_entries(json.loads(METRICS_FILE.read_text(encoding="utf-8")))
    metric_names = {e["name"] for e in metrics}
    assert metric_names == {
        'Product Count',
        'Material Count',
        'Supplier Count',
        'Sales Order Count',
        'Warehouse Count',
        'Available Stock',
        'Total Forecast Demand',
        'Open_Forecast_Count',
        'Total Signed Quantity',
        'Total Shipped Quantity',
        'Signing Events',
    }

    lp_payload = json.loads(LP_FILE.read_text(encoding="utf-8"))
    lp_metric_names = {
        spec["metric_name"]
        for group in lp_payload["bindings"]
        for spec in group["logic_properties"]
    }
    assert lp_metric_names == metric_names

    query_payload = json.loads(QUERY_FILE.read_text(encoding="utf-8"))
    query_metric_names = {case["metric_name"] for case in query_payload["cases"]}
    assert query_metric_names <= metric_names
    cases_by_id = {case["id"]: case for case in query_payload["cases"]}
    assert "open_forecast_count" in cases_by_id
    lp_names = {
        spec["name"]
        for group in lp_payload["bindings"]
        for spec in group["logic_properties"]
    }
    assert "available_qty_sum" in lp_names
    assert "available_inventory_qty" not in lp_names
    forecast_qty_all = cases_by_id["forecast_qty_all"]
    assert forecast_qty_all["expected_value"] == 115922
    assert 'Frozen CSV' in forecast_qty_all["note"]

    open_forecast_count = cases_by_id["open_forecast_count"]
    assert open_forecast_count["expected_value"] == 90
    assert '90 open forecasts' in open_forecast_count["note"]
    assert 'Frozen CSV' in open_forecast_count["note"]


def test_sales_quantity_metrics_match_filtered_csv_aggregates():
    import csv
    from decimal import Decimal

    metrics = {entry["name"]: entry for entry in extract_metric_entries(json.loads(METRICS_FILE.read_text()))}
    cases = {case["metric_name"]: case for case in json.loads(QUERY_FILE.read_text())["cases"]}
    with (PACK / "data" / "sales_order.csv").open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["product_code"] == "382-000005"]
    assert len(rows) == 40
    totals = []
    for name, field in [('Total Signed Quantity', "signing_quantity"), ('Total Shipped Quantity', "shipping_quantity")]:
        assert metrics[name]["scope_ref"] == "supply_ontology_en_salesorder"
        assert metrics[name]["calculation_formula"]["aggregation"] == {"property": field, "aggr": "sum"}
        case = cases[name]
        assert case["body"]["condition"] == {"field": "product_code", "operation": "==", "value": "382-000005"}
        total = sum(Decimal(row[field]) for row in rows)
        assert total == case["expected_value"]
        totals.append(total)
    assert totals[0] - totals[1] == 15
