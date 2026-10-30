"""The planning functions reproduce the v4 answers that need BOM netting."""

from pathlib import Path

import pytest
import yaml

from fn import CannotCompute, build_capacity, demand_coverage
from support_bkn_rows import csv_rows

V4 = Path(__file__).resolve().parents[2] / "bkn-eval" / "baselines" / "2026-10-30-business-scenarios-v4"
EXPECTED = {a["id"]: a["expected"] for a in yaml.safe_load((V4 / "answer-set-v4.yaml").read_text(encoding="utf-8"))["answers"]}
ROWS = csv_rows()


def capacity(product, **options):
    return build_capacity(ROWS, product, **options)


def test_plant_scope_builds_fewer_than_the_whole_company():
    expected = EXPECTED["Q-22"]
    assert capacity("382-000005", warehouse_scope="production_available")["buildable_qty"] == expected["plant_buildable"]
    assert capacity("382-000005")["buildable_qty"] == expected["company_buildable"]


def test_available_to_promise_keeps_signed_backlog_first():
    result = capacity("526-000006")
    expected = EXPECTED["Q-28"]
    assert (result["finished_goods_qty"], result["buildable_qty"], result["signed_backlog_qty"], result["available_to_promise"]) == (
        expected["fg_qty"], expected["buildable_qty"], expected["backlog_qty"], expected["available_to_promise"])
    assert capacity("P61-000351")["available_to_promise"] == EXPECTED["Q-30"]["supported_qty"]


def test_substitutes_raise_capacity_up_to_the_limiting_material():
    expected = EXPECTED["Q-29"]
    assert capacity("382-000005")["available_to_promise"] == expected["without_substitutes"]["promisable"]
    result = capacity("382-000005", substitute_enabled=True)
    assert result["available_to_promise"] == expected["with_substitutes"]["promisable"]
    assert result["buildable_qty"] == EXPECTED["Q-33"]["buildable_qty"]
    assert list(result["limiting_materials"]) == [EXPECTED["Q-33"]["limiting_material"]]


def test_in_transit_counts_only_by_date_unless_overdue_lines_are_chased():
    expected = EXPECTED["Q-46"]
    plain = capacity("U00-000080")
    assert plain["buildable_qty"] == expected["stock_only_buildable"]
    assert sorted(plain["limiting_materials"]) == expected["first_blocking_materials"]
    assert capacity("U00-000080", chase_overdue_po=True)["buildable_qty"] == expected["with_overdue_po_chased"]
    for product, extra in EXPECTED["Q-49"]["extra_buildable"].items():
        assert capacity(product, need_by="2026-09-30")["buildable_qty"] - capacity(product)["buildable_qty"] == extra


def test_backlog_shortage_is_the_bottom_level_material_gap():
    expected = EXPECTED["Q-25"]
    result = demand_coverage(ROWS, [{"product": "367-000097", "qty": 13}])["demands"][0]
    assert result["manufacture_qty"] == expected["short_sets"]
    assert result["shortages"] == expected["blocking_materials"]


def test_new_orders_share_one_pool_after_reserving_backlog():
    expected = EXPECTED["Q-31"]
    result = demand_coverage(ROWS, [{"product": "P61-000351", "qty": 60}, {"product": "U00-000151", "qty": 50}],
                             reserve_signed_backlog=True)
    assert [(d["covered"], d["shortages"]) for d in result["demands"]] == [
        (expected["P61_000351"]["covered"], expected["P61_000351"]["shortages"]),
        (expected["U00_000151"]["covered"], expected["U00_000151"]["shortages"])]
    chased = demand_coverage(ROWS, [{"product": "P61-000351", "qty": 60}], reserve_signed_backlog=True, chase_overdue_po=True)
    assert chased["demands"][0]["shortages"] == EXPECTED["Q-47"]["shortages"]


def test_work_order_does_not_use_finished_goods():
    expected = EXPECTED["Q-34"]
    shortages = demand_coverage(ROWS, [{"product": "367-000131", "qty": 100}], use_finished_goods=False)["demands"][0]["shortages"]
    assert len(shortages) == expected["shortage_material_count"]
    assert max(shortages, key=lambda code: (shortages[code], code)) == expected["largest_shortage"]


def test_product_without_bom_cannot_be_computed():
    with pytest.raises(CannotCompute):
        capacity("101-000002")
