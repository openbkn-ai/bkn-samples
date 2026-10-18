"""Each native Function is published as one readable source file."""

import ast
import sys
import types

import pytest

from function_catalog import FUNCTION_CATALOG
from function_source import build_function_code
from managed_execution import _OBJECT_TYPES, execute_from_bkn_rows
from register_native_function_toolbox import _operation_inputs
from support_bkn_rows import bkn_rows


# The runtime prepends its own imports and runs the code as __main__.
RUNTIME_PREFIX = "import sys\nimport json\nimport traceback\nimport sandbox_sdk\n\n# User code starts here\n"

CASES = {
    "bom_list": {"product": "382-000005", "depth": 1},
    "bom_shared_list": {"products": ["382-000005", "P61-000351"]},
    "material_where_used": {"material_code": "606-000989"},
    "layered_inventory": {"product": "U00-000151", "depth": 2},
    "substitute_status": {"product": "382-000005", "substitute_enabled": True},
    "theoretical_build": {"product": "U00-000151", "substitute_enabled": False},
    "total_sellable": {"product": "U00-000151", "substitute_enabled": False},
    "kitting_net_demand": {"product": "U00-000151", "qty": 100, "substitute_enabled": False},
    "shared_contention": {
        "demands": [{"product": "382-000005", "qty": 50}, {"product": "P61-000351", "qty": 60}],
        "substitute_enabled": False,
    },
    "max_build_without_po": {"product": "U00-000151", "substitute_enabled": False},
    "leadtime_days": {"material_code": "606-000989"},
    "supply_status": {"material_code": "606-000989", "due_date": "2026-09-30", "gross_requirement": 100},
    "open_forecast_count": {"report_grain": "full"},
    "backward_plan": {"forecast_id": "0000023181", "substitute_enabled": False},
}


def _matches(row, condition):
    operation = condition.get("operation")
    if operation == "and":
        return all(_matches(row, item) for item in condition.get("sub_conditions") or [])
    actual, value = str(row.get(condition.get("field"))), condition.get("value")
    if operation == "==":
        return actual == str(value)
    if operation == "!=":
        return actual != str(value)
    if operation == "in":
        return actual in {str(item) for item in value}
    raise AssertionError(operation)


@pytest.fixture
def fake_sdk(monkeypatch):
    rows = bkn_rows()
    dataset_by_object_type = {object_type: dataset for dataset, object_type in _OBJECT_TYPES.items()}

    def query_object_instance(**kwargs):
        result = rows.get(dataset_by_object_type[kwargs["ot_id"]], [])
        if kwargs.get("condition"):
            result = [row for row in result if _matches(row, kwargs["condition"])]
        offset = kwargs.get("offset", 0)
        return {"datas": result[offset : offset + kwargs["limit"]]}

    sdk = types.ModuleType("sandbox_sdk")
    sdk.tool = lambda func: func
    osdk = types.ModuleType("bkn_osdk")
    osdk_kn = types.ModuleType("bkn_osdk.kn")
    osdk_kn.query_object_instance = lambda kn_id, ot_id, **kwargs: query_object_instance(kn_id=kn_id, ot_id=ot_id, **kwargs)
    osdk.kn = osdk_kn
    monkeypatch.setitem(sys.modules, "sandbox_sdk", sdk)
    monkeypatch.setitem(sys.modules, "bkn_osdk", osdk)
    monkeypatch.setitem(sys.modules, "bkn_osdk.kn", osdk_kn)
    return rows


def _published_entry(operation):
    namespace = {"__name__": "__main__"}
    exec(compile(RUNTIME_PREFIX + build_function_code(operation), operation, "exec"), namespace)
    return namespace[f"{operation}_tool"]


@pytest.mark.parametrize("operation", FUNCTION_CATALOG)
def test_source_is_plain_and_has_one_sdk_entry(operation):
    source = build_function_code(operation)
    tree = ast.parse(source)
    entries = [
        node.name for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and any(isinstance(d, ast.Name) and d.id == "tool" for d in node.decorator_list)
    ]
    assert entries == [f"{operation}_tool"]
    for packed in ("base64", "zipfile", "b64decode", "_FIXED_OPERATION", "__future__", "def handler"):
        assert packed not in source
    for caller_context in ("resolved_context", "snapshot_id", "account_id"):
        assert caller_context not in source
    assert "from sandbox_sdk import tool" in source
    assert "from bkn_osdk.kn import query_object_instance" in source
    # The gateway and credentials come from the runtime, never from the code.
    assert "http://" not in source and "https://" not in source


@pytest.mark.parametrize("operation", FUNCTION_CATALOG)
def test_entry_declares_exactly_the_registered_inputs(operation):
    tree = ast.parse(build_function_code(operation))
    entry = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == f"{operation}_tool")
    assert [arg.arg for arg in entry.args.args] == [item["name"] for item in _operation_inputs(operation)]
    # Every input stays optional so missing values reach the calculation's own message.
    assert len(entry.args.defaults) == len(entry.args.args)


def test_source_carries_only_the_code_its_operation_reaches():
    lead_time = build_function_code("leadtime_days")
    assert "def leadtime_details(" in lead_time
    for other in ("def backward_plan(", "def net_requirements(", "def shared_contention(", "def run_bom_list("):
        assert other not in lead_time
    assert "def backward_plan(" in build_function_code("backward_plan")


@pytest.mark.parametrize("operation", FUNCTION_CATALOG)
def test_published_source_returns_the_tested_calculation(fake_sdk, operation):
    from managed_execution import load_bkn_rows

    params = CASES[operation]
    published = _published_entry(operation)(**params)

    loaded = load_bkn_rows(operation, sys.modules["bkn_osdk.kn"].query_object_instance, params)
    expected = execute_from_bkn_rows(operation, loaded, params)
    expected["data_source"] = {"knowledge_network_id": "supply_ontology_hand", "loaded_datasets": list(loaded)}
    assert published == expected


@pytest.mark.parametrize("numeric_ids", [False, True])
def test_published_backward_plan_reads_its_own_facts(fake_sdk, numeric_ids):
    # Current imports preserve strings; older resources can expose numeric IDs.
    if numeric_ids:
        fake_sdk["forecast"][:] = [
            {**row, "id": int(row["id"])} if str(row.get("id", "")).isdigit() else row
            for row in fake_sdk["forecast"]
        ]
    result = _published_entry("backward_plan")(
        product="U00-000080",
        forecast_id="0000023181",
        demand_end="2026-05-31",
        demand_qty=3000,
        substitute_enabled=False,
        report_grain="full_tree",
    )

    assert result["business_date"] == "2026-08-25"
    assert result["max_delay_days"] == 111
    assert result["node_count_total"] == 14
    assert result["data_source"]["knowledge_network_id"] == "supply_ontology_hand"
