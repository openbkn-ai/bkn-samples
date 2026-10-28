"""Contracts for native Functions that load their own BKN facts."""


def test_function_owned_loader_queries_each_required_object_type():
    from managed_execution import load_bkn_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        return {"datas": [{"material_code": kwargs["ot_id"]}]}

    rows = load_bkn_rows("supply_status", query_object_instance)

    assert set(rows) == {
        "material",
        "inventory",
        "purchase_order",
        "purchase_request",
        "mrp",
    }
    assert {call["ot_id"] for call in calls} == {
        "supply_ontology_en_material",
        "supply_ontology_en_inventory",
        "supply_ontology_en_po",
        "supply_ontology_en_pr",
        "supply_ontology_en_mrp",
    }
    assert all(call["kn_id"] == "supply_ontology_en" for call in calls)
    assert all(call["limit"] == 500 and call["offset"] == 0 for call in calls)


def test_function_owned_loader_does_not_accept_caller_context_or_identity():
    from managed_execution import load_bkn_rows

    assert "resolved_context" not in load_bkn_rows.__code__.co_varnames
    assert "snapshot_id" not in load_bkn_rows.__code__.co_varnames
    assert "account_id" not in load_bkn_rows.__code__.co_varnames
    assert "token" not in load_bkn_rows.__code__.co_varnames


def test_backward_plan_loader_uses_business_filters_instead_of_scanning_all_tables():
    from managed_execution import load_bkn_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"] == "supply_ontology_en_forecast":
            return {"datas": [{"id": "0000023181", "material_number": "U00-000080"}]}
        return {"datas": []}

    load_bkn_rows(
        "backward_plan",
        query_object_instance,
        {"product": "U00-000080", "forecast_id": "0000023181", "substitute_enabled": False},
    )

    by_type = {call["ot_id"]: call for call in calls}
    assert by_type["supply_ontology_en_forecast"]["condition"] == {
        "field": "id", "operation": "==", "value": "0000023181", "value_from": "const"
    }
    assert by_type["supply_ontology_en_bom"]["condition"] == {
        "field": "bom_material_code", "operation": "==", "value": "U00-000080", "value_from": "const"
    }
    condition = by_type["supply_ontology_en_material"]["condition"]
    assert condition["field"] == "material_code"
    assert condition["operation"] == "in"
    assert condition["value"] == ["U00-000080"]

    assert by_type["supply_ontology_en_mrp"]["condition"] == {
        "operation": "and",
        "sub_conditions": [
            {"field": "materialplanid_number", "operation": "in", "value": ["U00-000080"], "value_from": "const"},
            {"field": "closestatus_title", "operation": "!=", "value": 'Closed', "value_from": "const"},
        ],
    }

    assert by_type["supply_ontology_en_inventory"]["condition"] == {
        "operation": "and",
        "sub_conditions": [
            {"field": "material_code", "operation": "in", "value": ["U00-000080"], "value_from": "const"},
            {"field": "stock_status", "operation": "==", "value": 'Available', "value_from": "const"},
        ],
    }
    for object_type, field in (
        ("supply_ontology_en_po", "material_number"),
        ("supply_ontology_en_pr", "material_number"),
    ):
        assert by_type[object_type]["condition"] == {
            "operation": "and",
            "sub_conditions": [
                {"field": field, "operation": "in", "value": ["U00-000080"], "value_from": "const"},
                {"field": "rowclosestatus_title", "operation": "!=", "value": 'Closed', "value_from": "const"},
            ],
        }


def test_single_material_supply_status_filters_each_required_dataset():
    from managed_execution import load_bkn_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        return {"datas": []}

    load_bkn_rows(
        "supply_status",
        query_object_instance,
        {"material_code": "321-000569"},
    )

    expected_fields = {
        "supply_ontology_en_material": "material_code",
        "supply_ontology_en_inventory": "material_code",
        "supply_ontology_en_po": "material_number",
        "supply_ontology_en_pr": "material_number",
        "supply_ontology_en_mrp": "materialplanid_number",
    }
    for call in calls:
        assert call["condition"] == {
            "field": expected_fields[call["ot_id"]],
            "operation": "in",
            "value": ["321-000569"],
            "value_from": "const",
        }


def test_material_substitute_loader_reads_inventory_for_every_candidate():
    from managed_execution import load_bkn_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"] == "supply_ontology_en_bom":
            if kwargs["condition"].get("field") == "material_code":
                return {
                    "datas": [
                        {
                            "bom_material_code": "FG-1",
                            "parent_material_code": "P-1",
                            "alt_group_no": "7",
                            "material_code": "MAT-OLD",
                            "alt_priority": 0,
                        }
                    ]
                }
            return {
                "datas": [
                    {
                        "bom_material_code": "FG-1",
                        "parent_material_code": "P-1",
                        "alt_group_no": "7",
                        "material_code": "MAT-OLD",
                        "alt_priority": 0,
                    },
                    {
                        "bom_material_code": "FG-1",
                        "parent_material_code": "P-1",
                        "alt_group_no": "7",
                        "material_code": "MAT-NEW",
                        "alt_priority": 1,
                    },
                    {
                        "bom_material_code": "FG-1",
                        "parent_material_code": "P-2",
                        "alt_group_no": "9",
                        "material_code": "UNRELATED",
                        "alt_priority": 0,
                    },
                ]
            }
        return {"datas": []}

    load_bkn_rows(
        "substitute_status",
        query_object_instance,
        {"material_code": "MAT-OLD"},
    )

    inventory_calls = [
        call for call in calls if call["ot_id"] == "supply_ontology_en_inventory"
    ]
    assert [call["condition"] for call in inventory_calls] == [
        {
            "field": "material_code",
            "operation": "==",
            "value": "MAT-NEW",
            "value_from": "const",
        },
        {
            "field": "material_code",
            "operation": "==",
            "value": "MAT-OLD",
            "value_from": "const",
        },
    ]


def test_query_rows_stops_on_short_page_even_if_backend_includes_search_after():
    from managed_execution import _query_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        return {"datas": [{"material_code": "MAT-1"}], "search_after": ["stale"]}

    rows = _query_rows(
        query_object_instance,
        "supply_ontology_en_inventory",
        {"field": "material_code", "operation": "==", "value": "MAT-1"},
    )

    assert rows == [{"material_code": "MAT-1"}]
    assert len(calls) == 1


def test_bom_loader_reads_one_complete_root_bom_instead_of_recursive_parent_queries():
    from managed_execution import load_bkn_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"] != "supply_ontology_en_bom":
            return {"datas": []}
        root = kwargs["condition"]["value"]
        if root == "FG-1":
            return {
                "datas": [
                    {"bom_material_code": "FG-1", "parent_material_code": "FG-1", "material_code": "MAIN-1", "alt_group_no": "G1", "alt_priority": 0},
                    {"bom_material_code": "FG-1", "parent_material_code": "FG-1", "material_code": "ALT-1", "alt_group_no": "G1", "alt_priority": 1, "alt_method": 'Alternate'},
                    {"bom_material_code": "FG-1", "parent_material_code": "MAIN-1", "material_code": "RAW-1", "alt_priority": 0},
                ]
            }
        raise AssertionError(f"unexpected BOM root: {root}")

    load_bkn_rows("bom_list", query_object_instance, {"product": "FG-1", "depth": 3})

    bom_calls = [call for call in calls if call["ot_id"] == "supply_ontology_en_bom"]
    assert len(bom_calls) == 1
    assert bom_calls[0]["condition"] == {
        "field": "bom_material_code", "operation": "==", "value": "FG-1", "value_from": "const"
    }


def test_new_demand_backward_plan_filters_forecast_by_product():
    from managed_execution import load_bkn_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        return {"datas": []}

    load_bkn_rows(
        "backward_plan",
        query_object_instance,
        {"product": "U00-000080", "demand_qty": 1, "demand_end": "2026-09-01", "substitute_enabled": False},
    )

    forecast_call = next(call for call in calls if call["ot_id"] == "supply_ontology_en_forecast")
    assert forecast_call["condition"] == {
        "field": "material_number", "operation": "==", "value": "U00-000080", "value_from": "const"
    }


def test_inventory_only_kitting_scopes_stock_and_never_loads_purchase_orders():
    from managed_execution import load_bkn_rows

    calls = []

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"] == "supply_ontology_en_bom":
            return {
                "datas": [
                    {"bom_material_code": "FG-382", "parent_material_code": "FG-382", "material_code": "RM-001", "alt_priority": 0},
                    {"bom_material_code": "FG-382", "parent_material_code": "FG-382", "material_code": "RM-002", "alt_priority": 0},
                ]
            }
        return {"datas": []}

    load_bkn_rows(
        "kitting_net_demand",
        query_object_instance,
        {"product": "FG-382", "substitute_enabled": False},
    )

    by_type = {call["ot_id"]: call for call in calls}
    assert by_type["supply_ontology_en_inventory"]["condition"] == {
        "operation": "and",
        "sub_conditions": [
            {"field": "material_code", "operation": "in", "value": ["FG-382", "RM-001", "RM-002"], "value_from": "const"},
            {"field": "stock_status", "operation": "==", "value": 'Available', "value_from": "const"},
        ],
    }
    assert "supply_ontology_en_po" not in by_type


def test_backward_plan_scopes_large_purchase_request_material_scope_to_open_rows():
    from managed_execution import load_bkn_rows

    calls = []
    codes = [f"RM-{index:03d}" for index in range(55)]

    def query_object_instance(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"] == "supply_ontology_en_forecast":
            return {"datas": [{"id": "0000023181", "material_number": "FG-382"}]}
        if kwargs["ot_id"] == "supply_ontology_en_bom":
            return {
                "datas": [
                    {"bom_material_code": "FG-382", "parent_material_code": "FG-382", "material_code": code, "alt_priority": 0}
                    for code in codes
                ]
            }
        return {"datas": []}

    load_bkn_rows(
        "backward_plan",
        query_object_instance,
        {"product": "FG-382", "forecast_id": "0000023181", "substitute_enabled": False},
    )

    pr_calls = [call for call in calls if call["ot_id"] == "supply_ontology_en_pr"]
    assert len(pr_calls) == 1
    assert sorted(
        code
        for call in pr_calls
        for condition in call["condition"]["sub_conditions"]
        if condition["field"] == "material_number"
        for code in condition["value"]
    ) == sorted(["FG-382", *codes])
    conditions = pr_calls[0]["condition"]
    assert conditions["operation"] == "and"
    assert {"field": "rowclosestatus_title", "operation": "!=", "value": 'Closed', "value_from": "const"} in conditions["sub_conditions"]


def test_generated_native_function_uses_official_sdk_and_business_parameters_only():
    from native_function_bundle import build_native_function_code

    source = build_native_function_code(fixed_operation="backward_plan")

    assert "from sandbox_sdk import bkn" in source
    assert "@tool" in source
    assert "load_bkn_rows" in source
    assert "def handler" not in source
    assert "resolved_context" not in source
    assert "resolved_context_compressed" not in source
    assert "snapshot_id" not in source


def test_native_tool_schemas_never_expose_bkn_context_or_credentials():
    from register_native_function_toolbox import _tool_inputs

    forbidden = {
        "resolved_context",
        "resolved_context_compressed",
        "snapshot_id",
        "account_id",
        "token",
        "mcp",
    }
    for payload in _tool_inputs().values():
        assert not ({item["name"] for item in payload["inputs"]} & forbidden)


def test_kitting_loader_honors_explicit_production_warehouse_preset():
    from managed_execution import load_bkn_rows
    from fn.warehouse import PRODUCTION_AVAILABLE
    calls = []
    def query_object_instance(**kwargs):
        calls.append(kwargs)
        if kwargs["ot_id"] == "supply_ontology_en_bom":
            return {"datas": [{"bom_material_code": "P", "material_code": "L", "parent_material_code": "P", "bom_level": 1, "alt_priority": 0}]}
        return {"datas": []}
    load_bkn_rows("kitting_net_demand", query_object_instance,
                  {"product": "P", "substitute_enabled": False, "warehouse_scope": "production_available"})
    inventory = next(c for c in calls if c["ot_id"] == "supply_ontology_en_inventory")
    assert {"field": "warehouse", "operation": "in", "value": PRODUCTION_AVAILABLE,
            "value_from": "const"} in inventory["condition"]["sub_conditions"]
