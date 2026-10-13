"""Synthetic evidence vectors, independent of sample CSVs and evaluation gold."""
from datetime import date

from fn.backward_plan import backward_plan
from fn.snapshot import build_snapshot
from fn.supply_status import supply_status


def test_confirmed_coverage_excludes_undated_overdue_and_late_po():
    snap = build_snapshot({
        "material": [{"material_code": "M", "materialattr": 'Purchased'}],
        "inventory": [{"material_code": "M", "warehouse": "W", "available_inventory_qty": 10}],
        "po": [
            {"material_number": "M", "qty": q, "actqty": received, "deliverdate": day}
            for q, received, day in [(50, 10, "2026-09-08"), (100, 0, "2026-08-20"),
                                     (100, 0, ""), (100, 0, "2026-09-09")]]
    })
    result = supply_status(snap, "M", due_date="2026-09-08", gross_requirement=60,
                           today=date(2026, 8, 25))
    assert result["on_time_covered"] is False
    assert result["on_time_shortage_qty"] == 10
    assert result["supply"] == 50
    assert [r["eligibility"] for r in result["po_receipts"]] == [
        "on_time", "overdue_unconfirmed", "undated", "late"]
    # An uncertain additional receipt does not make confirmed coverage unknown.
    covered = supply_status(snap, "M", due_date="2026-09-08", gross_requirement=50,
                            today=date(2026, 8, 25))
    assert covered["on_time_covered"] is True
    assert covered["status"] == "sufficient"


def _stock_snapshot():
    return build_snapshot({
        "material": [{"material_code": "FG", "materialattr": 'Manufactured', "product_fixedleadtime": 0},
                     {"material_code": "M", "materialattr": 'Purchased', "purchase_fixedleadtime": 0}],
        "bom": [{"bom_material_code": "FG", "material_code": "M", "parent_material_code": "FG",
                 "bom_level": 1, "standard_usage": 1, "alt_priority": 0}],
        "inventory": [{"material_code": "FG", "warehouse": "CUSTOM", "available_inventory_qty": 10}],
    })


def test_customer_finished_goods_obey_explicit_warehouse_scope():
    snap = _stock_snapshot()
    included = backward_plan(snap, "FG", demand_qty=5, demand_end="2026-09-01",
                             business_date="2026-08-25", warehouse_scope=["CUSTOM"], substitute_enabled=False)
    assert included["finished_goods_qty"] == 10
    assert included["can_deliver_on_time"] is True
    excluded = backward_plan(snap, "FG", demand_qty=5, demand_end="2026-09-01",
                             business_date="2026-08-25", warehouse_scope=["OTHER"], substitute_enabled=False)
    assert excluded["finished_goods_qty"] == 0
    assert excluded["production_plan_required"] is True


def test_current_stock_does_not_confirm_past_delivery():
    snap = _stock_snapshot()
    result = backward_plan(snap, "FG", demand_qty=5, demand_end="2026-08-24",
                           business_date="2026-08-25", substitute_enabled=False)
    assert result["can_deliver_on_time"] is False
    assert result["delivery_commitment_status"] == "confirmed_late"
    assert result["customer_late_days"] == 1
    coverage = supply_status(snap, "FG", due_date="2026-08-24", gross_requirement=5,
                             today=date(2026, 8, 25))
    assert coverage["on_time_covered"] is False
    assert coverage["deadline_elapsed"] is True
