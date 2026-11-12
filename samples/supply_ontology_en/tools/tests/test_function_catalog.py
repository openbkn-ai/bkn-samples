"""Published Function metadata and the code bundle stay in step with the calculations."""

import re
import sys
import types

from function_catalog import FUNCTION_CATALOG, KIT_SCHEDULE
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
    preview = run(box_name='Supply_EN_Functions', apply=False)
    assert preview["operations"] == [*OPERATIONS, "kit_schedule", "kit_check_rule", "line_check_rule"]
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
    result = namespace["supply_function"](products=["526-000006"])
    assert result["products"][0]["available_to_promise"] == 8
    assert result["data_source"]["loaded_rows"]["sales_order"] > 0


def test_tool_names_and_descriptions_fit_the_platform_limits():
    # Toolbox names and descriptions must satisfy the operator-integration validator:
    # word characters or Chinese only, at most 50 characters; descriptions at most 255.
    import re
    from function_catalog import native_tool_description
    assert len(native_tool_description()) <= 255
    for spec in FUNCTION_CATALOG.values():
        assert re.fullmatch(r"[\w\u4e00-\u9fff]{1,50}", spec["name"]), spec["name"]
        assert len(spec["description"]) <= 255, spec["name"]


def test_bundled_kit_schedule_writes_the_plan_as_the_caller(monkeypatch):
    from kit_schedule import OT_PLAN
    query = FakeObjectQuery({OT_PLAN: []})
    sdk = types.ModuleType("sandbox_sdk")
    sdk.bkn = types.SimpleNamespace(query_object_instance=query)
    sdk.tool = lambda fn: fn
    calls = []

    def call(path, method="GET", body=None):
        calls.append((method, path, body))
        if method == "GET":
            return {"entries": [{"id": OT_PLAN, "data_source": {"type": "resource", "id": "res-plan"}}]}
        return {"id": path.rsplit("/", 1)[1]}
    osdk = types.ModuleType("bkn_osdk")
    osdk.call = call
    monkeypatch.setitem(sys.modules, "sandbox_sdk", sdk)
    monkeypatch.setitem(sys.modules, "bkn_osdk", osdk)
    for name in [m for m in sys.modules if m in ("fn", "managed_execution", "kit_schedule") or m.startswith("fn.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "path", list(sys.path))
    namespace: dict = {}
    exec(build_native_function_code(fixed_operation="kit_schedule"), namespace)
    result = namespace["kit_schedule"](bill_no="YCD2026102100000073", product_code="P61-000331", line_code="L-SZ-UGV",
                                       planned_start="2027-04-12", planned_finish="2027-04-14", plan_status="Scheduled",
                                       source_scenario="April schedule", planner="Owen Brooks")
    assert result["action"] == "created" and result["plan"]["kit_status"] == "Covered"
    method, path, body = calls[-1]
    assert (method, path) == ("PUT", "/api/vega-backend/v1/resources/res-plan/data/KP-2026102100000073-P61-000331-01")
    assert body["plan_id"] == "KP-2026102100000073-P61-000331-01" and body["quantity"] == 1


def test_three_plan_actions_are_object_actions_run_by_the_kit_schedule_tool():
    from register_native_function_toolbox import kit_action_definitions, kit_tool_inputs
    inputs = {item["name"] for item in kit_tool_inputs()}
    actions = {a["id"]: a for a in kit_action_definitions("supply_ontology_en", "box", "tool-kit")}
    assert set(actions) == {f"supply_ontology_en_kitplan_{k}" for k in ("create", "adjust", "cancel")}
    for action in actions.values():
        assert action["operation_config"] == {"type": "object"}
        assert action["object_type_id"] == "supply_ontology_en_kitplan"
        assert action["action_source"] == {"type": "tool", "box_id": "box", "tool_id": "tool-kit"}
        assert {p["name"] for p in action["parameters"]} <= inputs
    create = actions["supply_ontology_en_kitplan_create"]
    assert create["action_type"] == "add" and {p["value_from"] for p in create["parameters"]} == {"property"}
    cancel = {p["name"]: p for p in actions["supply_ontology_en_kitplan_cancel"]["parameters"]}
    assert cancel["plan_status"] == {"name": "plan_status", "type": "string", "value_from": "const",
                                     "comment": cancel["plan_status"]["comment"], "value": "Cancelled"}
    assert cancel["plan_id"]["value_from"] == "property"
    assert re.fullmatch(r"[\w一-鿿]{1,50}", KIT_SCHEDULE["name"]) and len(KIT_SCHEDULE["description"]) <= 255
