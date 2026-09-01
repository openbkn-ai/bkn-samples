"""Native Function source must select the official sandbox SDK entry mode."""

import sys
import types

from support_bkn_rows import bkn_rows


def test_native_function_source_is_compilable_sdk_tool_code():
    from native_function_bundle import build_native_function_code

    source = build_native_function_code(fixed_operation="backward_plan")

    compile(source, "native-function.py", "exec")
    assert "@tool" in source
    assert "def handler" not in source
    assert "_FIXED_OPERATION = 'backward_plan'" in source


def test_native_function_source_never_asks_caller_for_a_data_snapshot():
    from native_function_bundle import build_native_function_code

    source = build_native_function_code(fixed_operation="bom_list")

    for forbidden in (
        "resolved_context",
        "resolved_context_compressed",
        "snapshot_id",
        "account_id",
        "token",
    ):
        assert forbidden not in source
    assert "bkn.query_object_instance" in source
    assert "load_bkn_rows" in source


def test_generated_native_function_loads_its_own_bkn_rows(monkeypatch):
    from native_function_bundle import build_native_function_code

    rows = bkn_rows()
    dataset_by_object_type = {
        "supply_ontology_hand_forecast": "forecast",
        "supply_ontology_hand_bom": "bom",
        "supply_ontology_hand_material": "material",
        "supply_ontology_hand_inventory": "inventory",
        "supply_ontology_hand_po": "purchase_order",
        "supply_ontology_hand_pr": "purchase_request",
        "supply_ontology_hand_mrp": "mrp",
    }
    # Vega infers purely numeric business IDs as numbers when the resource is
    # scanned.  Keep this mock aligned with the deployed knowledge network:
    # the source CSV keeps `0000023181`, whereas Context Loader returns 23181.
    rows["forecast"] = [
        {**row, "id": int(row["id"])} if str(row.get("id", "")).isdigit() else row
        for row in rows["forecast"]
    ]
    calls = []

    def matches(row, condition):
        operation = condition.get("operation")
        if operation == "and":
            return all(matches(row, item) for item in condition.get("sub_conditions") or [])
        field = condition.get("field")
        value = condition.get("value")
        actual = str(row.get(field))
        if operation == "==":
            return actual == str(value)
        if operation == "!=":
            return actual != str(value)
        if operation == "in":
            return actual in {str(item) for item in value}
        return True

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        result = rows[dataset_by_object_type[kwargs["ot_id"]]]
        condition = kwargs.get("condition") or {}
        if condition:
            result = [row for row in result if matches(row, condition)]
        offset = kwargs.get("offset", 0)
        limit = kwargs.get("limit", len(result))
        return {"datas": result[offset : offset + limit]}

    fake_sdk = types.ModuleType("sandbox_sdk")
    fake_sdk.tool = lambda func: func
    fake_sdk.bkn = types.SimpleNamespace(query_object_instance=query_object_instance)
    monkeypatch.setitem(sys.modules, "sandbox_sdk", fake_sdk)

    namespace: dict[str, object] = {}
    exec(build_native_function_code(fixed_operation="backward_plan"), namespace)
    result = namespace["supply_function"](
        product="U00-000080",
        forecast_id="0000023181",
        demand_end="2026-05-31",
        demand_qty=3000,
        substitute_enabled=False,
    )

    assert result["business_date"] == "2026-08-25"
    assert result["max_delay_days"] == 176
    assert result["data_source"]["knowledge_network_id"] == "supply_ontology_hand"
    assert {call["ot_id"] for call in calls} == set(dataset_by_object_type)
