"""Synthetic contract vectors for the Stage B ``backward_plan`` pure function.

These tests intentionally build in-memory snapshots.  They must not read the
experience-pack CSV files or the business Q&A evaluation set.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from fn.backward_plan import backward_plan
from fn.errors import CannotCompute
from fn.snapshot import build_snapshot


TODAY = date(2026, 8, 14)
DEMAND_END = "2026-08-31"
FORECAST_ID = "FC-001"
PRODUCT = "FG-001"
WAREHOUSE = "苏州电子原料仓"
NODE_LIMIT = 5000

NODE_FIELDS = {
    "material_code",
    "parent_material_code",
    "bom_level",
    "usage_per_unit",
    "gross_requirement",
    "start_date",
    "end_date",
    "lead_time_days",
    "available_qty",
    "in_transit_qty",
    "supply_status",
    "delay_class",
    "delay_days",
    "evidence",
}


def material(
    code: str,
    *,
    attr: str = "外购",
    purchase_lt: int | str | None = 0,
    production_lt: int | str | None = 0,
) -> dict:
    return {
        "material_code": code,
        "materialattr": attr,
        "purchase_fixedleadtime": purchase_lt,
        "product_fixedleadtime": production_lt,
    }


def bom_row(
    child: str,
    *,
    parent: str = PRODUCT,
    level: int = 1,
    usage: float = 1,
) -> dict:
    return {
        "bom_material_code": PRODUCT,
        "material_code": child,
        "parent_material_code": parent,
        "bom_level": level,
        "standard_usage": usage,
        "alt_priority": 0,
        "alt_method": "主料",
    }


def substitute_bom_row(
    child: str,
    *,
    parent: str = PRODUCT,
    level: int = 1,
    usage: float = 1,
    group: str = "G1",
) -> dict:
    return {
        **bom_row(child, parent=parent, level=level, usage=usage),
        "alt_group_no": group,
        "alt_priority": 1,
        "alt_method": "替代",
    }


def forecast(
    *,
    forecast_id: str = FORECAST_ID,
    product: str = PRODUCT,
    end: str = DEMAND_END,
    qty: float = 10,
) -> dict:
    return {
        "id": forecast_id,
        "material_number": product,
        "enddate": end,
        "qty": qty,
    }


def inventory(code: str, qty: float, *, warehouse: str = WAREHOUSE) -> dict:
    return {
        "material_code": code,
        "warehouse": warehouse,
        "available_inventory_qty": qty,
    }


def po(
    code: str,
    *,
    qty: float,
    actqty: float = 0,
    deliverdate: str = "2026-08-20",
    closed: bool = False,
) -> dict:
    return {
        "material_number": code,
        "qty": qty,
        "actqty": actqty,
        "deliverdate": deliverdate,
        "rowclosestatus_title": "已关闭" if closed else "未关闭",
    }


def pr(code: str, *, qty: float = 1, closed: bool = False) -> dict:
    return {
        "material_number": code,
        "qty": qty,
        "joinqty": 0,
        "rowclosestatus_title": "已关闭" if closed else "未关闭",
    }


def mrp(code: str, *, closed: bool = False) -> dict:
    return {
        "materialplanid_number": code,
        "closestatus_title": "已关闭" if closed else "未关闭",
    }


def rows(
    *,
    bom: list[dict] | None = None,
    materials: list[dict] | None = None,
    forecasts: list[dict] | None = None,
    inventories: list[dict] | None = None,
    purchase_orders: list[dict] | None = None,
    purchase_requests: list[dict] | None = None,
    mrps: list[dict] | None = None,
) -> dict[str, list[dict]]:
    return {
        "forecast": forecasts if forecasts is not None else [forecast()],
        "bom": bom if bom is not None else [bom_row("RM-001")],
        "material": materials
        if materials is not None
        else [
            material(PRODUCT, attr="自制", production_lt=5),
            material("RM-001", purchase_lt=3),
        ],
        "inventory": inventories or [],
        "purchase_order": purchase_orders or [],
        "purchase_request": purchase_requests or [],
        "mrp": mrps or [],
    }


def run_plan(snapshot=None, **overrides):
    arguments = {
        "product": PRODUCT,
        "forecast_id": FORECAST_ID,
        "demand_end": DEMAND_END,
        "demand_qty": 10,
        "warehouse_scope": "production_available",
        "substitute_enabled": False,
        "report_grain": "full_tree",
        "business_date": TODAY.isoformat(),
    }
    arguments.update(overrides)
    return backward_plan(snapshot or build_snapshot(rows()), **arguments)


def node(result: dict, code: str, *, parent: str | None = None) -> dict:
    matches = [
        item
        for item in result["nodes"]
        if item["material_code"] == code
        and (parent is None or item["parent_material_code"] == parent)
    ]
    assert len(matches) == 1
    return matches[0]


def assert_node_contract(item: dict) -> None:
    assert NODE_FIELDS <= item.keys()
    assert isinstance(item["evidence"], dict)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("product", ""),
        ("demand_end", ""),
        ("demand_end", "2026-02-30"),
        ("demand_qty", 0),
        ("demand_qty", -1),
        ("substitute_enabled", None),
        ("report_grain", "detail"),
    ],
)
def test_rejects_invalid_required_input(field, value):
    with pytest.raises((CannotCompute, ValueError)):
        run_plan(forecast_id=None, **{field: value})


def test_business_date_defaults_to_sample_baseline_instead_of_system_today():
    result = backward_plan(
        build_snapshot(rows()),
        PRODUCT,
        forecast_id=FORECAST_ID,
        demand_end=DEMAND_END,
        demand_qty=10,
        warehouse_scope="production_available",
        substitute_enabled=False,
        report_grain="summary",
    )
    assert result["business_date"] == "2026-08-25"


def test_business_date_is_parsed_and_echoed():
    result = backward_plan(
        build_snapshot(rows()),
        PRODUCT,
        forecast_id=FORECAST_ID,
        demand_end=DEMAND_END,
        demand_qty=10,
        warehouse_scope="production_available",
        substitute_enabled=False,
        report_grain="summary",
        business_date="2026-08-25",
    )
    assert result["business_date"] == "2026-08-25"


def test_rejects_missing_forecast():
    with pytest.raises(CannotCompute):
        run_plan(forecast_id="FC-MISSING")


def test_allows_new_demand_without_a_forecast_id():
    result = run_plan(forecast_id=None)

    assert result["forecast_id"] is None


def test_forecast_mode_derives_product_quantity_and_due_date_from_forecast():
    result = backward_plan(
        build_snapshot(rows()),
        forecast_id=FORECAST_ID,
        substitute_enabled=False,
        report_grain="summary",
    )

    assert result["forecast_id"] == FORECAST_ID
    assert result["product_code"] == PRODUCT
    assert result["demand_qty"] == 10
    assert result["demand_end"] == DEMAND_END
    assert result["product_code"] == PRODUCT
    assert result["demand_qty"] == 10


@pytest.mark.parametrize(
    ("forecast_override", "request_override"),
    [
        ({"product": "FG-OTHER"}, {}),
        ({"end": "2026-09-01"}, {}),
        ({"qty": 11}, {}),
        ({}, {"product": "FG-OTHER"}),
        ({}, {"demand_end": "2026-09-01"}),
        ({}, {"demand_qty": 11}),
    ],
)
def test_rejects_forecast_request_mismatch(forecast_override, request_override):
    synthetic = rows(forecasts=[forecast(**forecast_override)])
    with pytest.raises(CannotCompute):
        run_plan(build_snapshot(synthetic), **request_override)


def test_rejects_empty_bom():
    with pytest.raises(CannotCompute):
        run_plan(build_snapshot(rows(bom=[])))


def test_builds_root_and_child_calendar_windows_with_attribute_leadtimes():
    synthetic = rows(
        bom=[
            bom_row("BUY", usage=2),
            bom_row("OUTSOURCE", usage=1),
            bom_row("MAKE", usage=1),
            bom_row("NO-LT", usage=1),
        ],
        materials=[
            material(PRODUCT, attr="自制", production_lt=5),
            material("BUY", attr="外购", purchase_lt=3),
            material("OUTSOURCE", attr="委外", purchase_lt=4, production_lt=99),
            material("MAKE", attr="自制", purchase_lt=99, production_lt=2),
            material("NO-LT", attr="外购", purchase_lt=None),
        ],
        mrps=[mrp("BUY"), mrp("OUTSOURCE"), mrp("MAKE"), mrp("NO-LT")],
    )

    result = run_plan(build_snapshot(synthetic))

    root = node(result, PRODUCT)
    assert_node_contract(root)
    assert root["parent_material_code"] == ""
    assert root["bom_level"] == 0
    assert root["usage_per_unit"] == 1
    assert root["gross_requirement"] == 10
    assert root["end_date"] == "2026-08-31"
    assert root["start_date"] == "2026-08-26"
    assert root["lead_time_days"] == 5

    expected = {
        "BUY": (2, 20, 3, "2026-08-25", "2026-08-22"),
        "OUTSOURCE": (1, 10, 4, "2026-08-25", "2026-08-21"),
        "MAKE": (1, 10, 2, "2026-08-25", "2026-08-23"),
        "NO-LT": (1, 10, 0, "2026-08-25", "2026-08-24"),
    }
    for code, (usage, gross, leadtime, end, start) in expected.items():
        item = node(result, code)
        assert_node_contract(item)
        assert item["parent_material_code"] == PRODUCT
        assert item["bom_level"] == 1
        assert item["usage_per_unit"] == usage
        assert item["gross_requirement"] == gross
        assert item["lead_time_days"] == leadtime
        assert item["end_date"] == end
        assert item["start_date"] == start


def test_accumulates_usage_and_gross_requirement_along_each_path():
    synthetic = rows(
        bom=[
            bom_row("SUB", usage=2),
            bom_row("LEAF", parent="SUB", level=2, usage=3),
        ],
        materials=[
            material(PRODUCT, attr="自制", production_lt=1),
            material("SUB", attr="自制", production_lt=2),
            material("LEAF", purchase_lt=4),
        ],
        mrps=[mrp("SUB"), mrp("LEAF")],
    )

    result = run_plan(build_snapshot(synthetic))

    assert node(result, "SUB")["usage_per_unit"] == 2
    assert node(result, "SUB")["gross_requirement"] == 20
    leaf = node(result, "LEAF")
    assert leaf["usage_per_unit"] == 6
    assert leaf["gross_requirement"] == 60
    assert leaf["end_date"] == "2026-08-26"


@pytest.mark.parametrize("substitute_enabled", [False, True])
def test_substitute_rows_stay_out_of_the_main_backward_tree(substitute_enabled):
    """主树只用主料 BOM；替代策略必须显式，但不改变倒排树结构。"""
    synthetic = rows(
        bom=[bom_row("MAIN"), substitute_bom_row("ALT")],
        materials=[
            material(PRODUCT, attr="自制", production_lt=5),
            material("MAIN", attr="外购", purchase_lt=3),
            material("ALT", attr="外购", purchase_lt=1),
        ],
        mrps=[mrp("MAIN"), mrp("ALT")],
    )

    result = run_plan(
        build_snapshot(synthetic), substitute_enabled=substitute_enabled
    )

    assert {item["material_code"] for item in result["nodes"]} == {PRODUCT, "MAIN"}
    assert result["node_count_total"] == 2
    assert result["substitute_enabled"] is substitute_enabled


def test_satisfied_node_uses_one_day_gantt_bar():
    """已满足（无 MRP 且有供给）→ 条长 1 天，不按标准提前期排。"""
    synthetic = rows(inventories=[inventory("RM-001", 10)])

    item = node(run_plan(build_snapshot(synthetic)), "RM-001")

    assert item["supply_status"] == "sufficient"
    assert item["lead_time_days"] == 3
    assert item["end_date"] == "2026-08-25"
    assert item["start_date"] == "2026-08-24"


def test_counts_available_and_only_open_po_remainder_while_pr_affects_status_only():
    synthetic = rows(
        inventories=[
            inventory("RM-001", 4),
            inventory("RM-001", 100, warehouse="隔离仓"),
        ],
        purchase_orders=[
            po("RM-001", qty=8, actqty=3, deliverdate="2026-08-20"),
            po("RM-001", qty=50, closed=True),
            po("RM-001", qty=2, actqty=3),
        ],
        purchase_requests=[pr("RM-001", qty=90)],
        mrps=[mrp("RM-001")],
    )

    item = node(run_plan(build_snapshot(synthetic)), "RM-001")

    assert_node_contract(item)
    assert item["available_qty"] == 4
    assert item["in_transit_qty"] == 5
    assert item["available_qty"] + item["in_transit_qty"] == 9
    assert item["supply_status"] == "po_in_transit"
    assert item["evidence"]["open_pr_qty"] == 90
    assert item["evidence"]["supply_qty"] == 9


def test_rejects_missing_material_master():
    """缺物料主数据与 leadtime_days 合同一致：抛 CannotCompute，不做 soft-fail。"""
    synthetic = rows(
        bom=[bom_row("NO-MASTER")],
        materials=[material(PRODUCT, attr="自制", production_lt=5)],
    )
    with pytest.raises(CannotCompute):
        run_plan(build_snapshot(synthetic))


def status_snapshot(status: str):
    child = "RM-STATUS"
    synthetic = rows(
        bom=[bom_row(child)],
        materials=[
            material(PRODUCT, attr="自制", production_lt=5),
            material(
                child,
                attr="自制" if status in {"child_short", "unscheduled", "plan_gap"} else "外购",
                purchase_lt=2,
                production_lt=2,
            ),
        ],
    )
    if status == "sufficient":
        synthetic["inventory"] = [inventory(child, 10)]
    elif status == "anomaly":
        pass
    elif status == "po_overdue":
        synthetic["mrp"] = [mrp(child)]
        synthetic["purchase_order"] = [
            po(child, qty=1, deliverdate="2026-08-14")
        ]
    elif status == "deadline_risk":
        synthetic["mrp"] = [mrp(child)]
        synthetic["purchase_order"] = [
            po(child, qty=1, deliverdate="2026-08-26")
        ]
    elif status == "no_pr":
        synthetic["mrp"] = [mrp(child)]
    elif status == "no_po":
        synthetic["mrp"] = [mrp(child)]
        synthetic["purchase_request"] = [pr(child)]
    elif status == "po_in_transit":
        synthetic["mrp"] = [mrp(child)]
        synthetic["purchase_request"] = [pr(child)]
        synthetic["purchase_order"] = [
            po(child, qty=1, deliverdate="2026-08-20")
        ]
    elif status == "unscheduled":
        pass
    elif status == "plan_gap":
        synthetic["mrp"] = [mrp(child)]
    elif status == "child_short":
        synthetic["bom"].append(
            bom_row("RM-LEAF", parent=child, level=2)
        )
        synthetic["material"].append(material("RM-LEAF", attr="外购"))
        synthetic["mrp"] = [mrp(child)]
    else:  # pragma: no cover - guards the test factory itself
        raise AssertionError(status)
    return build_snapshot(synthetic), child


@pytest.mark.parametrize(
    "expected_status",
    [
        "sufficient",
        "anomaly",
        "po_overdue",
        "deadline_risk",
        "no_pr",
        "no_po",
        "po_in_transit",
        "child_short",
        "unscheduled",
        "plan_gap",
    ],
)
def test_integrates_all_ten_dated_supply_statuses(expected_status):
    snapshot, child = status_snapshot(expected_status)
    result = run_plan(snapshot)
    assert node(result, child)["supply_status"] == expected_status
    assert result["supply_status_summary"][expected_status] >= 1


def test_classifies_type_a_delay_and_sets_product_delivery_result():
    synthetic = rows(
        forecasts=[forecast(end="2026-08-17")],
        materials=[
            material(PRODUCT, attr="自制", production_lt=1),
            material("RM-001", attr="外购", purchase_lt=5),
        ],
        purchase_requests=[pr("RM-001")],
        mrps=[mrp("RM-001")],
    )

    result = run_plan(
        build_snapshot(synthetic),
        demand_end="2026-08-17",
    )

    item = node(result, "RM-001")
    assert item["end_date"] == "2026-08-15"
    assert item["delay_class"] == "A"
    assert item["delay_days"] == 4
    assert result["delay_a"][0]["material_code"] == "RM-001"
    assert result["max_delay_days"] == 4
    assert result["can_deliver_on_time"] is False


def test_classifies_type_b_delay_from_late_po():
    synthetic = rows(
        purchase_orders=[
            po("RM-001", qty=1, deliverdate="2026-08-30")
        ],
        purchase_requests=[pr("RM-001")],
        mrps=[mrp("RM-001")],
    )

    result = run_plan(build_snapshot(synthetic))

    item = node(result, "RM-001")
    assert item["end_date"] == "2026-08-25"
    assert item["delay_class"] == "B"
    assert item["delay_days"] == 5
    assert result["delay_b"][0]["material_code"] == "RM-001"
    assert result["max_delay_days"] == 5
    assert result["can_deliver_on_time"] is False


def test_repeated_material_paths_keep_the_largest_delay():
    synthetic = rows(
        forecasts=[forecast(end="2026-08-20")],
        bom=[
            bom_row("P1"),
            bom_row("P2"),
            bom_row("SHARED", parent="P1", level=2),
            bom_row("SHARED", parent="P2", level=2),
        ],
        materials=[
            material(PRODUCT, attr="自制", production_lt=1),
            material("P1", attr="自制", production_lt=1),
            material("P2", attr="自制", production_lt=5),
            material("SHARED", attr="外购", purchase_lt=5),
        ],
        mrps=[mrp("P1"), mrp("P2"), mrp("SHARED")],
    )

    result = run_plan(
        build_snapshot(synthetic),
        demand_end="2026-08-20",
    )

    shared_nodes = [
        item for item in result["nodes"] if item["material_code"] == "SHARED"
    ]
    assert len(shared_nodes) == 2
    assert sorted(item["delay_days"] for item in shared_nodes) == [3, 7]
    shared_delay = [
        item for item in result["delay_a"] if item["material_code"] == "SHARED"
    ]
    assert len(shared_delay) == 1
    assert shared_delay[0]["delay_days"] == 7
    assert result["max_delay_days"] == 7
    assert result["can_deliver_on_time"] is False


def test_zero_delay_means_product_can_deliver_on_time():
    synthetic = rows(inventories=[inventory("RM-001", 10)])
    result = run_plan(build_snapshot(synthetic))
    assert result["max_delay_days"] == 0
    assert result["can_deliver_on_time"] is True


def test_finished_goods_coverage_bypasses_manufacturing_plan_for_customer_delivery():
    synthetic = rows(
        inventories=[inventory(PRODUCT, 10, warehouse="苏州成品仓")],
    )

    result = run_plan(build_snapshot(synthetic), demand_qty=10)

    assert result["can_deliver_on_time"] is True
    assert result["fulfillment_mode"] == "finished_goods"
    assert result["finished_goods_qty"] == 10
    assert result["remaining_finished_goods_qty"] == 0
    assert result["customer_earliest_available_date"] == TODAY.isoformat()
    assert result["customer_late_days"] == 0
    assert result["production_plan_required"] is False
    assert result["node_count_total"] == 0


def test_customer_date_fields_use_business_date_and_critical_shortage_lead_time():
    synthetic = rows(
        forecasts=[forecast(end="2026-08-17")],
        materials=[
            material(PRODUCT, attr="自制", production_lt=1),
            material("RM-001", attr="外购", purchase_lt=5),
        ],
        purchase_requests=[pr("RM-001")],
        mrps=[mrp("RM-001")],
    )

    result = run_plan(build_snapshot(synthetic), demand_end="2026-08-17")

    assert result["fulfillment_mode"] == "production_plan"
    assert result["customer_earliest_available_date"] == "2026-08-19"
    assert result["customer_late_days"] == 2
    assert result["production_plan_required"] is True


def test_skips_cycle_and_emits_warning():
    synthetic = rows(
        bom=[
            bom_row("SUB"),
            bom_row(PRODUCT, parent="SUB", level=2),
        ],
        materials=[
            material(PRODUCT, attr="自制", production_lt=1),
            material("SUB", attr="自制", production_lt=1),
        ],
        mrps=[mrp("SUB")],
    )

    result = run_plan(build_snapshot(synthetic))

    assert [item["material_code"] for item in result["nodes"]] == [
        PRODUCT,
        "SUB",
    ]
    assert result["node_count_total"] == 2
    assert any("环路" in warning for warning in result["warnings"])


def flat_tree_rows(child_count: int) -> dict[str, list[dict]]:
    """root + child_count 个可达主料子件，用于验证固定 5000 节点上限。"""
    children = [f"RM-{index:05d}" for index in range(child_count)]
    return rows(
        bom=[bom_row(code) for code in children],
        materials=[material(PRODUCT, attr="自制", production_lt=1)]
        + [material(code, attr="外购", purchase_lt=1) for code in children],
    )


def test_accepts_tree_at_the_fixed_node_limit():
    result = run_plan(build_snapshot(flat_tree_rows(NODE_LIMIT - 1)))
    assert result["node_count_total"] == NODE_LIMIT


def test_rejects_tree_above_the_fixed_node_limit():
    with pytest.raises(CannotCompute):
        run_plan(build_snapshot(flat_tree_rows(NODE_LIMIT)))


def test_node_limit_is_not_a_caller_parameter():
    with pytest.raises(TypeError):
        run_plan(max_nodes=2)


def test_report_grain_filters_nodes_without_changing_total_count():
    synthetic = rows(
        bom=[bom_row("SAFE"), bom_row("RISK")],
        materials=[
            material(PRODUCT, attr="自制", production_lt=1),
            material("SAFE", attr="外购", purchase_lt=1),
            material("RISK", attr="外购", purchase_lt=1),
        ],
        inventories=[inventory("SAFE", 10)],
        mrps=[mrp("RISK")],
    )
    snapshot = build_snapshot(synthetic)

    full = run_plan(snapshot, report_grain="full_tree")
    summary = run_plan(snapshot, report_grain="summary")

    assert full["node_count_total"] == 3
    assert summary["node_count_total"] == 3
    assert {item["material_code"] for item in full["nodes"]} == {
        PRODUCT,
        "SAFE",
        "RISK",
    }
    assert {item["material_code"] for item in summary["nodes"]} == {
        PRODUCT,
        "RISK",
    }
    for item in full["nodes"] + summary["nodes"]:
        assert_node_contract(item)


def test_build_snapshot_does_not_mutate_synthetic_rows():
    synthetic = rows()
    original = deepcopy(synthetic)
    run_plan(build_snapshot(synthetic))
    assert synthetic == original
