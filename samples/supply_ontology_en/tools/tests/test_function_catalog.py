"""Agent-facing descriptions for the supply calculation toolbox."""

from __future__ import annotations


def test_function_catalog_exposes_all_business_operations_with_concise_guidance():
    from function_catalog import FUNCTION_CATALOG

    assert len(FUNCTION_CATALOG) == 17
    assert set(FUNCTION_CATALOG) == {
        "shortage_rule",
        "material_coverage",
        "replenishment_draft",
        "bom_list",
        "bom_shared_list",
        "layered_inventory",
        "substitute_status",
        "theoretical_build",
        "total_sellable",
        "kitting_net_demand",
        "shared_contention",
        "max_build_without_po",
        "leadtime_days",
        "supply_status",
        "open_forecast_count",
        "backward_plan",
        "material_where_used",
    }
    for operation, spec in FUNCTION_CATALOG.items():
        assert spec["operation"] == operation
        assert spec["name"].strip()
        description = spec["description"]
        assert description.startswith('Use case:')
        assert 'Input:' in description
        assert 'Result:' in description
        assert 'Do not use for' not in description
        assert len(description) <= 260


def test_catalogue_guides_agents_from_business_question_to_one_capability():
    from function_catalog import FUNCTION_CATALOG

    reverse = FUNCTION_CATALOG["material_where_used"]
    assert reverse["name"] == 'Where_Used'
    assert 'which products' in reverse["description"]
    assert reverse["minimum_business_inputs"] == ["material_code"]

    sellable = FUNCTION_CATALOG["total_sellable"]
    assert 'stock' in sellable["use_when"]
    assert 'backward plan' in sellable["do_not_use_when"]

    backward = FUNCTION_CATALOG["backward_plan"]
    assert 'finished stock' in backward["do_not_use_when"]

    contention = FUNCTION_CATALOG["shared_contention"]
    assert 'multiple products' in contention["use_when"]


def test_similar_capacity_functions_state_their_business_result_boundary():
    from function_catalog import FUNCTION_CATALOG

    assert 'excludes finished goods and incoming supply' in FUNCTION_CATALOG["theoretical_build"]["description"]
    assert 'finished stock, manufacturing capacity and total sellable' in FUNCTION_CATALOG["total_sellable"]["description"]
    assert 'shared component structure without stock or allocation analysis' in FUNCTION_CATALOG["bom_shared_list"]["description"]
    assert 'coverage, all shortages' in FUNCTION_CATALOG["kitting_net_demand"]["description"]
    assert 'suggested replenishment' in FUNCTION_CATALOG["kitting_net_demand"]["description"]
    assert 'per-demand coverage and shortages' in FUNCTION_CATALOG["shared_contention"]["description"]
    assert 'forecast ID and alternate policy' in FUNCTION_CATALOG["backward_plan"]["description"]
    assert 'Default business date: 2026-08-25' in FUNCTION_CATALOG["backward_plan"]["description"]
    assert "affected_product_count" in FUNCTION_CATALOG["material_where_used"]["description"]


def test_native_tool_inputs_expose_one_discoverable_tool_per_operation():
    from function_catalog import FUNCTION_CATALOG
    from register_native_function_toolbox import LEGACY_TOOL_NAME, _tool_inputs

    payloads = _tool_inputs()
    assert set(payloads) == set(FUNCTION_CATALOG)

    for operation, spec in FUNCTION_CATALOG.items():
        payload = payloads[operation]
        assert payload["name"] == spec["name"]
        assert payload["description"] == spec["description"]
        assert "operation" not in {item["name"] for item in payload["inputs"]}
        assert "resolved_context" not in {item["name"] for item in payload["inputs"]}
        assert {item["type"] for item in payload["inputs"]} <= {
            "string", "number", "boolean", "array", "object"
        }
    assert LEGACY_TOOL_NAME not in {payload["name"] for payload in payloads.values()}
    kitting_inputs = {item["name"] for item in payloads["kitting_net_demand"]["inputs"]}
    assert "report_grain" in kitting_inputs
    contention_inputs = {item["name"] for item in payloads["shared_contention"]["inputs"]}
    assert "report_grain" in contention_inputs

    contention = {item["name"]: item for item in payloads["shared_contention"]["inputs"]}
    assert '{"product":"382-000005","qty":50}' in contention["demands"]["description"]
    assert contention["substitute_enabled"]["required"] is True

    backward = {item["name"]: item for item in payloads["backward_plan"]["inputs"]}
    assert backward["substitute_enabled"]["required"] is True
    assert 'leading zeroes' in backward["forecast_id"]["description"]


def test_public_guide_only_directs_users_to_native_functions():
    from pathlib import Path

    package = Path(__file__).resolve().parents[2]
    text = (package / "docs" / "import-guide.en-US.md").read_text(encoding="utf-8")

    assert "tools/fn/" in text
    assert 'Native Function Toolbox' in text
    assert "resolved_context" in text
    assert "host.docker.internal" not in text
    assert "FUNCTION_SERVICE_URL" not in text
