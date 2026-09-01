"""Agent-facing descriptions for the supply calculation toolbox."""

from __future__ import annotations


def test_function_catalog_exposes_all_business_operations_with_concise_guidance():
    from function_catalog import FUNCTION_CATALOG

    assert len(FUNCTION_CATALOG) == 14
    assert set(FUNCTION_CATALOG) == {
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
        assert description.startswith("适用场景：")
        assert "输入：" in description
        assert "结果：" in description
        assert "不要用于" not in description
        assert len(description) <= 260


def test_catalogue_guides_agents_from_business_question_to_one_capability():
    from function_catalog import FUNCTION_CATALOG

    reverse = FUNCTION_CATALOG["material_where_used"]
    assert reverse["name"] == "物料反查产品"
    assert "哪些产品" in reverse["description"]
    assert reverse["minimum_business_inputs"] == ["material_code"]

    sellable = FUNCTION_CATALOG["total_sellable"]
    assert "现货" in sellable["use_when"]
    assert "倒排" in sellable["do_not_use_when"]

    backward = FUNCTION_CATALOG["backward_plan"]
    assert "成品现货" in backward["do_not_use_when"]

    contention = FUNCTION_CATALOG["shared_contention"]
    assert "多个产品" in contention["use_when"]


def test_similar_capacity_functions_state_their_business_result_boundary():
    from function_catalog import FUNCTION_CATALOG

    assert "不含成品库存和在途" in FUNCTION_CATALOG["theoretical_build"]["description"]
    assert "成品可用、理论可产和合计可售" in FUNCTION_CATALOG["total_sellable"]["description"]
    assert "共同子料结构，不含库存或争用判断" in FUNCTION_CATALOG["bom_shared_list"]["description"]
    assert "默认返回齐套结论、全部缺料清单" in FUNCTION_CATALOG["kitting_net_demand"]["description"]
    assert "建议补货量" in FUNCTION_CATALOG["kitting_net_demand"]["description"]
    assert "默认返回逐单满足状态和缺料清单" in FUNCTION_CATALOG["shared_contention"]["description"]
    assert "预测单时只需预测单号和替代料策略" in FUNCTION_CATALOG["backward_plan"]["description"]
    assert "Sample 默认业务日期为 2026-08-25" in FUNCTION_CATALOG["backward_plan"]["description"]
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
    assert "前导零" in backward["forecast_id"]["description"]


def test_delivery_docs_only_direct_users_to_the_native_function_entry():
    from pathlib import Path

    package = Path(__file__).resolve().parents[2]
    for path in (
        package / "docs" / "能力口径清单.md",
        package / "docs" / "动力层落地说明书.md",
        package / "docs" / "动力层建设方案.md",
        package / "docs" / "场景驱动的供应链动态能力设计.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "14 个" not in text
        assert "supply_chain_compute" not in text
        assert "host.docker.internal:8765" not in text
        assert "71600d21-c9f6-4336-bfbf-95bfb3654674" not in text
        assert "242385da-f2d1-4264-84ac-ee7b10cdd76d" not in text
        assert "函数尚未做成独立算子" not in text

    delivery = (package / "docs" / "动力层落地说明书.md").read_text(encoding="utf-8")
    assert "register_native_function_toolbox.py" in delivery
    assert "物料反查产品" in delivery


def test_action_catalog_does_not_present_local_dry_runs_as_platform_writes():
    from pathlib import Path

    package = Path(__file__).resolve().parents[2]
    text = (package / "docs" / "catalog" / "actions.md").read_text(encoding="utf-8")

    assert "未绑定实际 Tool" in text
    assert "不可执行" in text
    assert "dry-run" in text
    assert "不得" in text


def test_delivery_guide_does_not_hard_code_deployment_specific_skill_ids():
    from pathlib import Path

    package = Path(__file__).resolve().parents[2]
    text = (package / "docs" / "动力层落地说明书.md").read_text(encoding="utf-8")

    for retired_id in (
        "158aee6d-067a-41ca-b382-d9a9a1e33275",
        "03c91afa-4aef-4e5b-899d-881ac1739d7f",
        "fba4903b-1e15-4353-9e23-66fd5d2d1bd5",
    ):
        assert retired_id not in text
    assert "openbkn --json skill list --limit 100" in text


def test_online_function_docs_describe_the_function_owned_bkn_read_contract():
    from pathlib import Path

    package = Path(__file__).resolve().parents[2]
    for path in (
        package / "docs" / "quickstart" / "online-openbkn.md",
        package / "docs" / "catalog" / "functions.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "sandbox_sdk.bkn" in text
        assert "resolved_context" not in text
        assert "FUNCTION_SERVICE_URL" not in text
