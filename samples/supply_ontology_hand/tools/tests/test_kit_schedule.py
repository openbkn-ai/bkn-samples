import csv
from datetime import datetime

import pytest

from fn import CannotCompute, DEFAULT_BUSINESS_DATE
from fn.kitplan import KIT_COVERED, KIT_PENDING, KIT_SHORT
from fn.kitrules import kit_rule
from kit_schedule import OT_PLAN, moment, schedule
from support_bkn_rows import DATA, FakeObjectQuery, csv_rows

NOW = datetime(2026, 11, 12, 10, 30, 0)


def history():
    with (DATA / "kit_schedule_plan.csv").open(encoding="utf-8") as fh:
        return [{k: v for k, v in row.items() if v != ""} for row in csv.DictReader(fh)]


class Store:
    """The plan dataset: written documents become plan objects for the next query."""

    def __init__(self):
        self.plans = {row["plan_id"]: row for row in history()}
        self.writes = []

    def query(self):
        return FakeObjectQuery({OT_PLAN: list(self.plans.values())})

    def write(self, plan_id, row):
        self.writes.append((plan_id, row))
        self.plans[plan_id] = row


def facts():
    read = lambda name: list(csv.DictReader((DATA / f"{name}.csv").open(encoding="utf-8")))
    rows = {**csv_rows(), "forecast": read("erp_mds_forecast"), "work_order": read("erp_production_work_order")}
    return rows, {r["material_code"]: r for r in read("erp_material")}


def as_task(plan):
    return {"key": plan["plan_id"], "start": plan["planned_start"], "resource": plan["line_code"], "values": plan}


def rule_result(plans, plan_id):
    """What the schedule Gantt's kit check says about one plan, among all the given plans."""
    rows, materials = facts()
    tasks = [as_task(p) for p in plans]
    return next(r for r in kit_rule(tasks, rows, materials=materials, business_date=DEFAULT_BUSINESS_DATE, others=tasks)
                if r["key"] == plan_id)


def assert_record_matches_rule(plan, rule):
    expected = KIT_COVERED if rule["pass"] is True else KIT_PENDING if rule.get("severity") == "soft" else KIT_SHORT
    assert plan["kit_status"] == expected, (plan, rule)
    assert plan.get("kit_date") == rule["at"], (plan, rule)


def run(store, **params):
    return schedule(params, store.query(), store.write, now=NOW)


def test_dates_are_normalised_to_the_plant_time_zone():
    assert moment("2027-05-10", "08:00:00") == "2027-05-10T08:00:00+08:00"
    assert moment("2027-05-10 09:15", "08:00:00") == "2027-05-10T09:15:00+08:00"
    assert moment("2027-05-10T09:15:00+08:00", "08:00:00") == "2027-05-10T09:15:00+08:00"


def test_scheduling_a_demand_creates_one_plan_with_its_kit_check():
    store = Store()
    result = run(store, bill_no="YCD2026100200000062", product_code="U00-000151", line_code="L-UR-NAV",
                 planned_start="2027-05-10", planned_finish="2027-05-14", plan_status="已排",
                 source_scenario="五月排产", planner="朱杰倩")
    plan = result["plan"]
    assert result["action"] == "created" and plan["plan_id"] == "KP-2026100200000062-U00-000151-01"
    assert plan["quantity"] == 500 and plan["reschedule_count"] == 0 and "previous_finish" not in plan
    assert plan["planned_at"] == f"{DEFAULT_BUSINESS_DATE}T10:30:00+08:00"
    assert_record_matches_rule(plan, rule_result(list(store.plans.values()), plan["plan_id"]))
    assert [w[0] for w in store.writes] == [plan["plan_id"]]


def test_scheduling_the_same_demand_again_updates_it_and_counts_the_move():
    store = Store()
    first = run(store, bill_no="YCD2026100200000062", product_code="U00-000151", line_code="L-UR-NAV",
                planned_start="2027-05-10", planned_finish="2027-05-14", plan_status="已排")["plan"]
    again = run(store, bill_no="YCD2026100200000062", product_code="U00-000151", line_code="L-UR-NAV",
                planned_start="2027-05-11", planned_finish="2027-05-15", plan_status="已排")
    assert again["action"] == "updated" and again["plan"]["plan_id"] == first["plan_id"]
    assert again["plan"]["reschedule_count"] == 1 and again["plan"]["previous_finish"] == first["planned_finish"]
    assert len(store.plans) == len(history()) + 1


def test_adjusting_a_selected_plan_keeps_its_status():
    store = Store()
    adjusted = run(store, plan_id="KP-2026111400000075-367-000131-01", bill_no="YCD2026111400000075",
                   product_code="367-000131", plan_status="已确认", line_code="L-SZ-UAV",
                   planned_start="2027-02-16 08:00:00", planned_finish="2027-03-03 20:00:00", planner="朱杰倩")
    assert adjusted["action"] == "updated"
    assert adjusted["plan"]["plan_status"] == "已确认" and adjusted["plan"]["reschedule_count"] == 1


def test_cancelling_frees_the_demand_for_a_new_plan():
    store = Store()
    cancelled = run(store, plan_id="KP-2026090400000052-ALL-01", bill_no="YCD2026090400000052", product_code="",
                    plan_status="已取消", planner="朱杰倩")
    assert cancelled["action"] == "cancelled" and cancelled["plan"]["plan_status"] == "已取消"
    with pytest.raises(CannotCompute):
        run(store, plan_id="KP-2026090400000052-ALL-01", plan_status="已取消")
    again = run(store, bill_no="YCD2026090400000052", product_code="", line_code="L-SZ-UGV",
                planned_start="2027-03-30", planned_finish="2027-04-06", plan_status="已排")
    assert again["action"] == "created" and again["plan"]["plan_id"] == "KP-2026090400000052-ALL-02"
    assert "quantity" not in again["plan"] and "product_code" not in again["plan"]


@pytest.mark.parametrize("line", ["L-UR-AD", "F-SZ", "L-NOPE"])
def test_a_demand_goes_only_to_a_line_that_builds_it(line):
    with pytest.raises(CannotCompute):
        run(Store(), bill_no="YCD2026100200000062", product_code="U00-000151", line_code=line,
            planned_start="2027-05-10", planned_finish="2027-05-14")


def test_closed_or_unknown_demand_and_reversed_dates_are_refused():
    store = Store()
    with pytest.raises(CannotCompute):
        run(store, bill_no="YCD2025120300000014", product_code="", line_code="L-UR-AD",
            planned_start="2027-03-01", planned_finish="2027-03-05")
    with pytest.raises(CannotCompute):
        run(store, bill_no="YCD2026100200000062", product_code="U00-000151", line_code="L-UR-NAV",
            planned_start="2027-05-14", planned_finish="2027-05-10")
    assert store.writes == []


def test_installed_plans_record_what_the_kit_check_shows():
    plans = history()
    for plan in plans:
        assert_record_matches_rule(plan, rule_result(plans, plan["plan_id"]))


def test_moving_a_plan_in_production_keeps_it_kitted():
    """F21: a confirmed plan whose production started was recorded short after a move, unlike the check."""
    store = Store()
    plan_id = "KP-2026100800000069-734-000001-01"
    moved = run(store, plan_id=plan_id, bill_no="YCD2026100800000069", product_code="734-000001", plan_status="已确认",
                line_code="L-SZ-UGV", planned_start="2027-02-22", planned_finish="2027-03-03")["plan"]
    assert moved["kit_status"] == "齐套" and "shortage_note" not in moved
    assert_record_matches_rule(moved, rule_result(list(store.plans.values()), plan_id))


def test_a_short_record_names_its_own_start_even_before_the_business_date():
    store = Store()
    plan_id = "KP-2026091600000057-382-000005-01"
    moved = run(store, plan_id=plan_id, bill_no="YCD2026091600000057", product_code="382-000005",
                line_code="L-UR-AD", planned_start="2027-02-20", planned_finish="2027-02-24")["plan"]
    assert "2027-02-20" in moved["shortage_note"]
    assert_record_matches_rule(moved, rule_result(list(store.plans.values()), plan_id))


def test_a_plan_kitted_once_purchase_requests_are_placed_is_recorded_as_pending_order():
    """F28: the check lets the plan be adopted (soft), so the record does not call it short; the note keeps the requests to place."""
    store = Store()
    plan = run(store, bill_no="YCD2026070700000039", product_code="U00-000080", line_code="L-UR-NAV",
               planned_start="2027-07-31", planned_finish="2027-08-06", plan_status="已排")["plan"]
    rule = rule_result(list(store.plans.values()), plan["plan_id"])
    assert rule["pass"] is False and rule["severity"] == "soft"
    assert plan["kit_status"] == KIT_PENDING and plan["kit_date"] <= "2027-07-31"
    assert "2027-07-31" in plan["shortage_note"] and "未下采购申请" in plan["shortage_note"]
    assert_record_matches_rule(plan, rule)
