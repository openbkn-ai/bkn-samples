"""Read cost of the schedule rule tools: the service reads, not the netting, set their run time."""

import time

from fn.kitrules import kit_detail, kit_rule
from managed_execution import PROPERTIES, load_bkn_rows
from schedule_rules import kit_check
from support_bkn_rows import DATA, FakeObjectQuery, csv_rows
import csv


def plans():
    with (DATA / "kit_schedule_plan.csv").open(encoding="utf-8") as fh:
        return [{"key": p["plan_id"], "start": p["planned_start"], "resource": p["line_code"],
                 "values": {k: v for k, v in p.items() if v}} for p in csv.DictReader(fh)]


def test_reads_ask_for_the_needed_fields_in_large_pages_without_substitutes():
    query = FakeObjectQuery()
    load_bkn_rows("demand_coverage", query, {"demands": [{"product": "382-000005", "qty": 10}], "need_by": "2027-03-31",
                                               "reserve_signed_backlog": True})
    assert all(call["limit"] == 10_000 and call["properties"] for call in query.calls)
    bom = [call for call in query.calls if call["ot_id"].endswith("_bom")]
    assert len(bom) == 1 and "alt_priority" in str(bom[0]["condition"])
    for name, fields in PROPERTIES.items():
        assert fields[0] in ("bom_version", "id", "entry_id", "sales_order_id"), name  # the key comes first


def test_a_check_reads_each_object_type_a_bounded_number_of_times():
    query = FakeObjectQuery({"supply_ontology_hand_kitplan": [t["values"] for t in plans()]})
    kit_check(plans(), query)
    per_type = {}
    for call in query.calls:
        per_type[call["ot_id"]] = per_type.get(call["ot_id"], 0) + 1
    # One query each; a result over 10 000 rows takes a second page.
    assert per_type["supply_ontology_hand_bom"] <= 2 and per_type["supply_ontology_hand_inventory"] <= 2
    assert sum(per_type.values()) <= 15


def test_two_hundred_plans_and_one_detail_compute_fast():
    rows = {**csv_rows(), "forecast": list(csv.DictReader((DATA / "erp_mds_forecast.csv").open(encoding="utf-8"))),
            "work_order": list(csv.DictReader((DATA / "erp_production_work_order.csv").open(encoding="utf-8")))}
    materials = {r["material_code"]: r for r in csv.DictReader((DATA / "erp_material.csv").open(encoding="utf-8"))}
    open_lines = [r for r in rows["forecast"] if r["startdate"] >= "2027-01-01"]
    tasks = [{"key": f"t{i}", "start": f"2027-0{3 + i % 5}-{1 + i % 27:02d}", "resource": "L",
              "values": {"bill_no": r["billno"], "product_code": r["material_number"], "plan_status": "已排"}}
             for i, r in enumerate((open_lines * 3)[:200])]
    started = time.perf_counter()
    assert len(kit_rule(tasks, rows, materials=materials)) == 200
    assert time.perf_counter() - started < 5
    started = time.perf_counter()
    assert kit_detail(plans()[-2], plans(), rows, materials=materials, query={"limit": 50})["title"]
    assert time.perf_counter() - started < 3


def test_the_demand_view_batch_checks_every_open_demand_quickly():
    """The demand view sends the plans and, for every open demand without one, the plan it would make: each of
    those is checked alone on top of the plans, which reuses the facts prepared once."""
    rows = {**csv_rows(), "forecast": list(csv.DictReader((DATA / "erp_mds_forecast.csv").open(encoding="utf-8"))),
            "work_order": list(csv.DictReader((DATA / "erp_production_work_order.csv").open(encoding="utf-8")))}
    materials = {r["material_code"]: r for r in csv.DictReader((DATA / "erp_material.csv").open(encoding="utf-8"))}
    proposals = [{"key": f"+demand/{r['id']}", "start": "2027-04-01", "resource": None,
                  "values": {"bill_no": r["billno"], "product_code": r["material_number"], "plan_status": "已排"}}
                 for r in rows["forecast"] if r["closestatus_title"] == "正常"][:187]
    started = time.perf_counter()
    assert len(kit_rule(plans() + proposals, rows, materials=materials, others=plans())) == len(plans()) + len(proposals)
    assert time.perf_counter() - started < 3

