"""Published Function metadata and the code bundle stay in step with the calculations."""

import sys
import types

from function_catalog import FUNCTION_CATALOG
from managed_execution import OPERATIONS
from native_function_bundle import build_native_function_code
from register_native_function_toolbox import _operation_inputs, run
from support_bkn_rows import FakeObjectQuery


def test_catalog_publishes_exactly_the_two_calculations():
    assert tuple(FUNCTION_CATALOG) == OPERATIONS
    for operation, spec in FUNCTION_CATALOG.items():
        names = {item["name"] for item in _operation_inputs(operation)}
        assert set(spec["minimum_business_inputs"]) <= names
        assert {"substitute_enabled", "warehouse_scope", "need_by", "chase_overdue_po"} <= names


def test_dry_run_lists_the_tools_without_calling_the_platform():
    preview = run(box_name="供应链原生计算函数", apply=False)
    assert preview["operations"] == list(OPERATIONS)
    assert preview["needs_external_service"] is False


def test_bundled_function_runs_with_the_sandbox_reader(monkeypatch):
    query = FakeObjectQuery()
    sdk = types.ModuleType("sandbox_sdk")
    sdk.bkn = types.SimpleNamespace(query_object_instance=query)
    sdk.tool = lambda fn: fn
    monkeypatch.setitem(sys.modules, "sandbox_sdk", sdk)
    for name in [m for m in sys.modules if m == "fn" or m.startswith("fn.") or m == "managed_execution"]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "path", list(sys.path))
    namespace: dict = {}
    exec(build_native_function_code(fixed_operation="build_capacity"), namespace)
    result = namespace["supply_function"](product="526-000006")
    assert result["available_to_promise"] == 8
    assert result["data_source"]["loaded_rows"]["sales_order"] > 0
