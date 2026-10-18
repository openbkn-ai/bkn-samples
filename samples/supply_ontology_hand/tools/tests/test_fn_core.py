"""CSV snapshot tests for KN function library (口径清单 §2)."""

from __future__ import annotations

import pytest

from fn import (
    CannotCompute,
    bom_list,
    bom_shared_list,
    kitting_net_demand,
    layered_inventory,
    leadtime_days,
    load_csv_snapshot,
    material_where_used,
    resolve_warehouse_scope,
    shared_contention,
    substitute_status,
    supply_status,
    theoretical_build,
    total_sellable,
)


@pytest.fixture(scope="module")
def snap():
    return load_csv_snapshot()


def test_warehouse_presets():
    prod = resolve_warehouse_scope("production_available")
    fg = resolve_warehouse_scope("finished_goods")
    assert len(prod) == 7
    assert "苏州半成品仓" in prod
    assert "昆山成品仓" not in prod
    assert fg == ["苏州成品仓", "乌鲁木齐成品仓", "哈尔滨成品仓"]
    assert resolve_warehouse_scope("all") == []


def test_bom_list_382_l1(snap):
    out = bom_list(snap, "382-000005", depth=1, include_substitute=False)
    assert out["l1_main_count"] == 9
    codes = [r["material_code"] for r in out["l1_lines"]]
    assert codes == [
        "791-000013",
        "606-000989",
        "606-000990",
        "528-000036",
        "791-000007",
        "994-000550",
        "468-000493",
        "468-000530",
        "791-000015",
    ]
    assert "available_qty" not in out["l1_lines"][0]


def test_bom_list_382_counts(snap):
    out = bom_list(snap, "382-000005", depth=None, include_substitute=False)
    assert out["rows_incl_root"] == 507
    assert out["line_count"] == 313
    assert out["unique_child_count"] == 272
    assert out["max_level"] == 5
    assert "lines" not in out
    assert out["report_grain"] == "summary"


def test_bom_list_full_output_is_explicit_and_paged(snap):
    first = bom_list(
        snap,
        "382-000005",
        depth=None,
        include_substitute=False,
        report_grain="full",
        page_size=100,
        offset=0,
    )
    second = bom_list(
        snap,
        "382-000005",
        depth=None,
        include_substitute=False,
        report_grain="full",
        page_size=100,
        offset=100,
    )

    assert len(first["lines"]) == 100
    assert first["next_offset"] == 100
    assert len(second["lines"]) == 100
    assert second["next_offset"] == 200


def test_bom_list_missing_product(snap):
    with pytest.raises(CannotCompute):
        bom_list(snap, "")


def test_material_where_used_returns_affected_root_products(snap):
    pcb = material_where_used(snap, "321-000569")
    assert pcb["affected_product_count"] == 3
    assert pcb["product_codes"] == ["P61-000328", "P61-000331", "P61-000351"]

    common = material_where_used(snap, "725-000226")
    assert common["affected_product_count"] == 30

    with pytest.raises(CannotCompute, match="物料编码"):
        material_where_used(snap, "")


def test_bom_shared_382_p61(snap):
    out = bom_shared_list(snap, ["382-000005", "P61-000351"], include_substitute=False)
    assert out["shared_count"] == 28
    assert "356-000081" in out["shared_codes"]


def test_bom_shared_three_products(snap):
    out = bom_shared_list(
        snap, ["382-000005", "P61-000351", "U00-000151"], include_substitute=False
    )
    assert out["shared_count"] == 11


def test_bom_shared_one_product(snap):
    with pytest.raises(CannotCompute):
        bom_shared_list(snap, ["382-000005"])


def test_substitute_status_382(snap):
    out = substitute_status(snap, "382-000005")
    assert out["has_alt_groups"] is True
    assert out["group_count"] == 70
    assert out["substitute_enabled"] == "unknown"


def test_substitute_status_accepts_a_component_material(snap):
    out = substitute_status(snap, material_code="356-000061")

    assert out["material_code"] == "356-000061"
    candidates = [
        member
        for group in out["groups"]
        for member in group["members"]
    ]
    target = next(item for item in candidates if item["material_code"] == "356-000356")
    assert target["available_qty"] == pytest.approx(500)


def test_leadtime(snap):
    assert leadtime_days(snap, "606-000989") == 14
    assert leadtime_days(snap, "382-000005") == 1
    assert leadtime_days(snap, "994-000550") == 35
    with pytest.raises(CannotCompute):
        leadtime_days(snap, "")


def test_theoretical_and_sellable_382_no_sub(snap):
    th = theoretical_build(snap, "382-000005", substitute_enabled=False)
    sell = total_sellable(snap, "382-000005", substitute_enabled=False)
    assert th["theoretical_build_qty"] == 0
    assert sell["fg_qty"] == pytest.approx(534, rel=0, abs=0.01)
    assert sell["total_sellable_qty"] == pytest.approx(534, rel=0, abs=0.01)
    assert "in_transit" not in sell or sell.get("include_in_transit") is False


def test_sellable_u00(snap):
    sell = total_sellable(snap, "U00-000151", substitute_enabled=False)
    assert sell["fg_qty"] == pytest.approx(3800, rel=0, abs=0.01)
    assert sell["total_sellable_qty"] >= sell["fg_qty"]


def test_theoretical_build_defaults_to_summary_and_full_keeps_constraints(snap):
    summary = theoretical_build(snap, "382-000005", substitute_enabled=False)
    full = theoretical_build(
        snap,
        "382-000005",
        substitute_enabled=False,
        report_grain="full",
    )

    assert summary["report_grain"] == "summary"
    assert "constraints" not in summary
    assert summary["constraint_count"] == len(full["constraints"])
    assert summary["theoretical_build_qty"] == full["theoretical_build_qty"]
    assert summary["bottleneck"] == full["bottleneck"]
    assert full["report_grain"] == "full"


def test_max_build_inherits_theoretical_summary_grain(snap):
    from fn import max_build_without_po

    summary = max_build_without_po(snap, "382-000005", substitute_enabled=False)
    full = max_build_without_po(
        snap,
        "382-000005",
        substitute_enabled=False,
        report_grain="full",
    )

    assert summary["scene"] == "inventory_build"
    assert "constraints" not in summary
    assert summary["constraint_count"] == len(full["constraints"])


def test_theoretical_build_rejects_unknown_report_grain(snap):
    with pytest.raises(CannotCompute, match="report_grain"):
        theoretical_build(
            snap,
            "382-000005",
            substitute_enabled=False,
            report_grain="detail",
        )


def test_kitting_382_50_not_s1(snap):
    out = kitting_net_demand(snap, "382-000005", qty=50, substitute_enabled=False)
    assert out["kitting_ok"] is False
    l1s = {g.get("l1_parent") for g in out["gaps"]} | {g["material_code"] for g in out["gaps"]}
    assert "791-000007" in l1s or "791-000015" in l1s
    assert "delay_a" not in out
    assert "supply_status" not in out
    assert all(
        gap["recommended_replenishment_qty"] == gap["net_requirement"]
        for gap in out["gaps"]
    )


def test_kitting_defaults_to_business_summary_and_full_keeps_all_lines(snap):
    summary = kitting_net_demand(
        snap, "382-000005", qty=50, substitute_enabled=False
    )
    full = kitting_net_demand(
        snap,
        "382-000005",
        qty=50,
        substitute_enabled=False,
        report_grain="full",
    )

    assert summary["report_grain"] == "summary"
    assert "lines" not in summary
    assert summary["line_count"] == len(full["lines"])
    assert summary["gap_count"] == len(summary["gaps"])
    assert summary["gaps"] == full["gaps"]
    assert full["report_grain"] == "full"
    assert full["line_count"] == len(full["lines"])


def test_kitting_rejects_unknown_report_grain(snap):
    with pytest.raises(CannotCompute, match="report_grain"):
        kitting_net_demand(
            snap,
            "382-000005",
            qty=50,
            substitute_enabled=False,
            report_grain="detail",
        )


def test_shared_contention_keeps_using_kitting_full_detail_internally(snap):
    result = shared_contention(
        snap,
        [
            {"product_code": "382-000005", "qty": 50},
            {"product_code": "P61-000351", "qty": 60},
        ],
        substitute_enabled=False,
        report_grain="full",
    )

    assert len(result["allocations"]) == 2
    assert all(allocation["lines"] for allocation in result["allocations"])


def test_shared_contention_defaults_to_business_summary_and_full_keeps_diagnostics(snap):
    demands = [
        {"product_code": "382-000005", "qty": 50},
        {"product_code": "P61-000351", "qty": 60},
    ]
    summary = shared_contention(snap, demands, substitute_enabled=False)
    full = shared_contention(
        snap, demands, substitute_enabled=False, report_grain="full"
    )

    assert summary["report_grain"] == "summary"
    assert summary["deduction_order"] == ["382-000005", "P61-000351"]
    assert "remaining" not in summary
    assert all("lines" not in allocation for allocation in summary["allocations"])
    assert all("shortage_count" in allocation for allocation in summary["allocations"])
    assert summary["all_satisfied"] == all(
        allocation["satisfied"] for allocation in full["allocations"]
    )
    assert summary["unsatisfied_demand_count"] == sum(
        not allocation["satisfied"] for allocation in full["allocations"]
    )
    assert full["report_grain"] == "full"
    assert "remaining" in full
    assert all(allocation["lines"] for allocation in full["allocations"])


def test_shared_contention_rejects_unknown_report_grain(snap):
    with pytest.raises(CannotCompute, match="report_grain"):
        shared_contention(
            snap,
            [
                {"product_code": "382-000005", "qty": 50},
                {"product_code": "P61-000351", "qty": 60},
            ],
            substitute_enabled=False,
            report_grain="detail",
        )


def test_supply_status_requires_due_date(snap):
    out = supply_status(snap, "791-000007", due_date=None, gross_requirement=50)
    assert out["status"] == "unknown"


def test_layered_inventory_382_l1(snap):
    out = layered_inventory(snap, "382-000005", depth=1)
    by_code = {r["material_code"]: r["available_qty"] for r in out["lines"]}
    assert by_code["791-000013"] == pytest.approx(1000, rel=0, abs=0.01)
    assert by_code["791-000007"] == pytest.approx(0, rel=0, abs=0.01)
    assert by_code["791-000015"] == pytest.approx(0, rel=0, abs=0.01)
    assert "reserved_qty" in out["lines"][0]
    assert len(out["warehouse_filter"]) == 7


def test_max_build_alias_equals_theoretical(snap):
    th = theoretical_build(snap, "382-000005", substitute_enabled=False)
    from fn import max_build_without_po

    mb = max_build_without_po(snap, "382-000005", substitute_enabled=False)
    assert mb["theoretical_build_qty"] == th["theoretical_build_qty"]
