"""The native Functions read only the facts a question needs and run the planning calculation."""

import pytest

from managed_execution import execute_from_bkn_rows, load_bkn_rows
from fn import CannotCompute
from support_bkn_rows import FakeObjectQuery


def run(operation, params):
    query = FakeObjectQuery()
    rows = load_bkn_rows(operation, query, params)
    return query, rows, execute_from_bkn_rows(operation, rows, params)


def object_types(query):
    return {call["ot_id"].removeprefix("supply_ontology_en_") for call in query.calls}


def test_capacity_reads_bom_stock_and_backlog_but_no_purchase_orders():
    query, rows, result = run("build_capacity", {"products": ["526-000006"]})
    assert object_types(query) == {"bom", "inventory", "salesorder"}
    assert all(r["stock_status"] == "Available" for r in rows["inventory"])
    assert result["products"][0]["available_to_promise"] == 8


def test_several_products_are_computed_independently_in_one_call():
    _, _, together = run("build_capacity", {"products": ["526-000006", "382-000005"]})
    assert [item["product"] for item in together["products"]] == ["526-000006", "382-000005"]
    for item in together["products"]:
        _, _, alone = run("build_capacity", {"products": [item["product"]]})
        assert alone["products"] == [item]


def test_purchase_orders_are_read_only_when_in_transit_is_asked_for():
    query, rows, result = run("build_capacity", {"products": ["U00-000080"], "chase_overdue_po": True})
    assert "po" in object_types(query)
    assert result["products"][0]["buildable_qty"] == 2972


def test_coverage_reads_sales_orders_only_to_reserve_backlog():
    query, _, result = run("demand_coverage", {"demands": [{"product": "367-000097", "qty": 13}]})
    assert object_types(query) == {"bom", "inventory"}
    assert result["demands"][0]["manufacture_qty"] == 4
    query, _, _ = run("demand_coverage", {"demands": [{"product": "P61-000351", "qty": 60}], "reserve_signed_backlog": True})
    assert "salesorder" in object_types(query)


def test_warehouse_scope_is_filtered_on_the_server():
    query, _, result = run("build_capacity", {"products": ["382-000005"], "warehouse_scope": "production_available"})
    inventory = next(c for c in query.calls if c["ot_id"].endswith("_inventory"))
    assert any(item.get("field") == "warehouse" for item in inventory["condition"]["sub_conditions"])
    assert result["products"][0]["buildable_qty"] == 34


@pytest.mark.parametrize("operation, params", [
    ("build_capacity", {}),
    ("build_capacity", {"products": []}),
    ("demand_coverage", {"demands": []}),
    ("demand_coverage", {"demands": [{"product": "382-000005"}]}),
    ("bom_list", {"product": "382-000005"}),
])
def test_incomplete_requests_are_refused_before_reading(operation, params):
    query = FakeObjectQuery()
    with pytest.raises(CannotCompute):
        load_bkn_rows(operation, query, params)
    assert query.calls == []
