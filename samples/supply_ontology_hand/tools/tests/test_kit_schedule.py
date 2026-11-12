import csv
from datetime import datetime

import pytest

from fn import CannotCompute, DEFAULT_BUSINESS_DATE
from fn.kitplan import kit_check
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
    expected = kit_check(csv_rows(), [{"product": "U00-000151", "qty": "500.000000"}], "2027-05-10",
                         business_date=DEFAULT_BUSINESS_DATE)
    assert (plan["kit_status"], plan.get("kit_date", "")) == (expected["kit_status"], expected["kit_date"])
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


def test_installed_scheduled_plans_carry_the_kit_check_of_their_start():
    rows = csv_rows()
    forecasts = list(csv.DictReader((DATA / "erp_mds_forecast.csv").open(encoding="utf-8")))
    for plan in history():
        if plan["plan_status"] != "已排":
            continue
        lines = [r for r in forecasts if r["billno"] == plan["bill_no"]
                 and (not plan.get("product_code") or r["material_number"] == plan["product_code"])]
        kit = kit_check(rows, [{"product": r["material_number"], "qty": r["qty"]} for r in lines],
                        plan["planned_start"], business_date=DEFAULT_BUSINESS_DATE)
        assert (plan["kit_status"], plan.get("kit_date", ""), plan.get("key_material", "")) == (
            kit["kit_status"], kit["kit_date"], kit["key_material"])
