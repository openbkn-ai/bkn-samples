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
        {"comment": "x", "entries": [{"name": "产品总数", "scope_ref": "ot"}]}
    )
    assert entries[0]["name"] == "产品总数"


def test_extract_entries_from_list():
    entries = extract_metric_entries([{"name": "物料总数"}])
    assert entries[0]["name"] == "物料总数"


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
                "display_name": "产品总数",
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
    assert values_close(540, 534)
    assert not values_close(600, 534)


def test_pack_payloads_exist_and_align():
    metrics = extract_metric_entries(json.loads(METRICS_FILE.read_text(encoding="utf-8")))
    metric_names = {e["name"] for e in metrics}
    assert metric_names == {
        "产品总数",
        "物料总数",
        "供应商总数",
        "销售订单数",
        "仓库数",
        "库存可用量",
        "预测需求量合计",
        "未关闭预测单数",
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
    assert forecast_qty_all["expected_value"] == 106422
    assert "POC 环境" in forecast_qty_all["note"]
    assert "M-07" in forecast_qty_all["note"]

    open_forecast_count = cases_by_id["open_forecast_count"]
    assert open_forecast_count["expected_value"] == 87
    assert "状态为“正常”" in open_forecast_count["note"]
    assert "POC 环境" in open_forecast_count["note"]
    assert "M-08" in open_forecast_count["note"]
