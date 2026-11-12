"""Schedule-Gantt rule tools: kit check on one shared pool, and line can build."""

import sys
import types

import pytest

from fn.kitrules import HARD, SOFT, kit_detail, kit_rule, line_rule
from native_function_bundle import build_native_function_code
from support_bkn_rows import FakeObjectQuery

BD = "2027-02-25"


def bom(product, *materials):
    rows = [dict(bom_material_code=product, bom_level=0, material_code=product, parent_material_code="", seq_no=1,
                 standard_usage=1, alt_priority=0, alt_part="", alt_group_no="0", material_name=product)]
    rows += [dict(bom_material_code=product, bom_level=1, material_code=m, parent_material_code=product, seq_no=i + 2,
                  standard_usage=1, alt_priority=0, alt_part="", alt_group_no="0", material_name=m) for i, m in enumerate(materials)]
    return rows


ROWS = {
    "bom": bom("P1", "M1") + bom("P2", "M1") + bom("P3", "M3"),
    "inventory": [dict(material_code="M1", stock_status="可用", warehouse="苏州装配原料仓", available_inventory_qty=100)],
    "purchase_order": [dict(material_number="M1", qty=50, actqty=0, deliverdate="2027-03-10", billno="PO-A", entry_id="E-A",
                            rowclosestatus_title="正常", rowterminatestatus_title="正常")],
    "sales_order": [],
    "forecast": [dict(billno="B1", material_number="P1", qty=80, closestatus_title="正常"),
                 dict(billno="B2", material_number="P2", qty=60, closestatus_title="正常"),
                 dict(billno="B3", material_number="P3", qty=5, closestatus_title="正常")],
}
MATERIALS = {"M1": {"material_name": "控制芯片", "purchase_fixedleadtime": 20},
             "M3": {"material_name": "包装箱", "purchase_fixedleadtime": 10}}


def task(key, bill, start, product="", line="L1", status="已排"):
    return {"key": key, "start": f"{start}T08:00:00+08:00", "end": None, "resource": line,
            "values": {"bill_no": bill, "product_code": product, "plan_status": status}}


def check(*tasks):
    return {r["key"]: r for r in kit_rule(list(tasks), ROWS, materials=MATERIALS, business_date=BD)}


def test_a_plan_covered_by_stock_passes():
    result = check(task("a", "B1", "2027-03-01"))["a"]
    assert result["pass"] is True and result["at"] == "2027-03-01"


def test_the_later_plan_is_short_and_names_the_plan_that_took_the_material():
    result = check(task("a", "B1", "2027-03-01"), task("b", "B2", "2027-03-05"))
    assert result["a"]["pass"] is True
    b = result["b"]
    assert (b["pass"], b["severity"], b["related"], b["at"], b["detail"]) == (False, HARD, ["a"], "2027-03-10", True)
    assert b["text"] == "缺料 1 种，关键：控制芯片 M1 在途 3/10 到" and len(b["text"]) <= 40
    assert b["counts"] == [{"label": "缺料物料", "value": 1}, {"label": "在途晚到", "value": 1}]


def test_moving_a_plan_earlier_hands_the_shortage_to_the_other():
    result = check(task("a", "B1", "2027-03-01"), task("b", "B2", "2027-02-28"))
    assert result["b"]["pass"] is True
    assert (result["a"]["pass"], result["a"]["related"], result["a"]["at"]) == (False, ["b"], "2027-03-10")


def test_confirmed_plans_draw_before_scheduled_ones_whatever_their_start():
    result = check(task("a", "B1", "2027-03-01"), task("b", "B2", "2027-03-05", status="已确认"))
    assert result["b"]["pass"] is True
    assert (result["a"]["pass"], result["a"]["related"]) == (False, ["b"])


def test_a_plan_whose_production_started_has_drawn_its_materials():
    rows = {**ROWS, "work_order": [dict(sourcebillnumber="B2", material_number="P2", taskstatus_title="开工")]}
    result = {r["key"]: r for r in kit_rule([task("a", "B1", "2027-03-01"), task("b", "B2", "2027-02-28", status="已确认")],
                                            rows, materials=MATERIALS, business_date=BD)}
    assert result["b"]["pass"] is True and result["a"]["pass"] is True


def test_material_not_on_order_is_estimated_by_lead_time():
    early = check(task("c", "B3", "2027-03-01"))["c"]
    assert (early["pass"], early["severity"], early["at"]) == (False, HARD, "2027-03-07")
    assert early["text"] == "缺料 1 种，关键：包装箱 M3 未下采购申请"
    assert {"label": "尚未下采购申请", "value": 1} in early["counts"]
    late = check(task("c", "B3", "2027-03-08"))["c"]
    assert (late["pass"], late["severity"]) == (False, SOFT)


def test_cancelled_is_not_applicable():
    result = check(task("x", "B1", "2027-03-01", status="已取消"), task("z", "B1", "2027-03-02"))
    assert result["x"]["pass"] is None and result["z"]["pass"] is True


def test_unknown_demand_fails_instead_of_passing():
    assert check(task("u", "NOPE", "2027-03-01"))["u"]["pass"] is False


# A product with many short materials, for the detail table.
MANY = {**ROWS, "bom": ROWS["bom"] + bom("P4", *[f"X{i:02d}" for i in range(12)]),
        "forecast": ROWS["forecast"] + [dict(billno="B4", material_number="P4", qty=10, closestatus_title="正常")],
        "purchase_order": ROWS["purchase_order"] + [
            dict(material_number="X00", qty=10, actqty=0, deliverdate="2027-04-20", billno="PO-L", entry_id="E-L",
                 rowclosestatus_title="正常", rowterminatestatus_title="正常"),
            dict(material_number="X01", qty=10, actqty=0, deliverdate="2027-01-20", billno="PO-O", entry_id="E-O",
                 rowclosestatus_title="正常", rowterminatestatus_title="正常")]}
MANY_MATERIALS = {**MATERIALS, **{f"X{i:02d}": {"material_name": f"零件{i:02d}", "purchase_fixedleadtime": i} for i in range(12)}}


def detail(query=None, locale="zh-CN"):
    return kit_detail(task("d", "B4", "2027-03-01"), [], MANY, materials=MANY_MATERIALS, business_date=BD,
                      locale=locale, query=query, kn_id="kn")


def test_detail_lists_short_materials_latest_ready_first_with_groups_and_links():
    table = detail()
    assert table["total"] == 12 and len(table["rows"]) == 12 and table["at"] == "2027-04-20"
    first = table["rows"][0]
    assert (first["id"], first["group"], first["key"]) == ("X00", "late_po", True)
    assert first["links"]["source"] == {"objectType": "kn_po", "key": "E-L"}
    groups = {g["id"]: g["count"] for g in table["groups"]}
    assert groups == {"late_po": 1, "overdue_po": 1, "no_pr": 10}
    assert [c["key"] for c in table["columns"]] == ["material", "parent", "need", "available", "short", "ready", "source"]
    assert table["conclusion"] == "缺料 12 种，最早 4/20 可齐套"
    readies = [r["cells"]["ready"] for r in table["rows"]]
    assert readies == sorted(readies, reverse=True)


def test_detail_pages_filters_by_group_key_and_search():
    page = detail({"offset": 5, "limit": 5})
    assert page["total"] == 12 and [r["id"] for r in page["rows"]] == [r["id"] for r in detail()["rows"][5:10]]
    assert [r["id"] for r in detail({"group": "overdue_po"})["rows"]] == ["X01"]
    assert [r["id"] for r in detail({"keyOnly": True})["rows"]] == ["X00"]
    assert [r["id"] for r in detail({"search": "零件07"})["rows"]] == ["X07"]
    assert detail({"search": "nothing"})["total"] == 0


def test_detail_labels_follow_the_locale():
    table = detail(locale="en-US")
    assert table["columns"][0]["label"] == "Material" and table["groups"][0]["label"] == "On order, arriving late"


def test_line_must_build_every_product_of_the_plan():
    lines = {"L1": {"line_code": "L1", "line_name": "无人机总装线", "line_kind": "产线", "product_lines": "无人机、无人车"},
             "F1": {"line_code": "F1", "line_name": "苏州工厂", "line_kind": "工厂"}}
    product_lines = {"P1": "无人机", "P2": "自动驾驶"}
    results = {r["key"]: r for r in line_rule([task("a", "B1", "2027-03-01"), task("b", "B2", "2027-03-01"),
                                               task("f", "B1", "2027-03-01", line="F1")],
                                              forecasts=ROWS["forecast"], lines=lines, product_lines=product_lines)}
    assert results["a"]["pass"] is True
    assert (results["b"]["pass"], results["b"]["severity"]) == (False, HARD)
    assert "无人机总装线" in results["b"]["text"] and "P2（自动驾驶）" in results["b"]["text"]
    assert results["f"]["pass"] is False


def test_more_than_two_hundred_tasks_is_an_error(monkeypatch):
    from schedule_rules import kit_check
    with pytest.raises(ValueError):
        kit_check([task(str(i), "B1", "2027-03-01") for i in range(201)], FakeObjectQuery())


def test_bundled_rule_tools_read_the_network_and_answer_per_task(monkeypatch):
    query = FakeObjectQuery()
    sdk = types.ModuleType("sandbox_sdk")
    sdk.bkn = types.SimpleNamespace(query_object_instance=query)
    sdk.tool = lambda fn: fn
    monkeypatch.setitem(sys.modules, "sandbox_sdk", sdk)
    for name in [m for m in sys.modules if m in ("fn", "managed_execution", "schedule_rules") or m.startswith("fn.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "path", list(sys.path))
    tasks = [task("p", "YCD2026102100000073", "2027-04-12", product="P61-000331", line="L-SZ-UGV"),
             task("q", "YCD2026100200000062", "2027-05-10", product="U00-000080", line="L-UR-AD")]
    for operation in ("kit_check_rule", "line_check_rule"):
        namespace: dict = {}
        exec(build_native_function_code(fixed_operation=operation), namespace)
        results = namespace["schedule_rule"](tasks=tasks, scenario={"edits": []})["results"]
        assert [r["key"] for r in results] == ["p", "q"] and all(r["pass"] in (True, False) for r in results)
        if operation == "line_check_rule":
            assert [r["pass"] for r in results] == [True, False]
        else:
            table = namespace["schedule_rule"](mode="detail", task=tasks[0], scenario={"edits": []}, locale="zh-CN",
                                               query={"offset": 0, "limit": 5})
            assert {"title", "conclusion", "at", "summary", "groups", "columns", "rows", "total"} <= set(table)
            assert table["title"].startswith("YCD2026102100000073 · ")


def test_rule_tool_names_and_descriptions_fit_the_platform_limits():
    import re
    from function_catalog import SCHEDULE_RULES
    for spec in SCHEDULE_RULES.values():
        assert re.fullmatch(r"[\w\u4e00-\u9fff]{1,50}", spec["name"]) and len(spec["description"]) <= 255


def test_rule_tool_use_rule_fits_the_platform_limit():
    from function_catalog import SCHEDULE_RULES
    assert all(len(spec["use_rule"]) <= 255 for spec in SCHEDULE_RULES.values())
