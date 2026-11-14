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
    """The tasks as the scheduling page sends them: the plans themselves, so they share the stock."""
    return {r["key"]: r for r in kit_rule(list(tasks), ROWS, materials=MATERIALS, business_date=BD, others=list(tasks))}


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
    osdk = types.ModuleType("bkn_osdk")
    osdk.call = lambda *a, **k: (_ for _ in ()).throw(AssertionError("not used inside an interaction"))
    monkeypatch.setitem(sys.modules, "sandbox_sdk", sdk)
    monkeypatch.setitem(sys.modules, "bkn_osdk", osdk)
    monkeypatch.setenv("BKN_CONVERSATION_ID", "conv-1")  # inside an interaction
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


def test_a_partly_started_plan_still_checks_its_other_products():
    rows = {**ROWS, "forecast": ROWS["forecast"] + [dict(billno="B5", material_number="P1", qty=80, closestatus_title="正常"),
                                                    dict(billno="B5", material_number="P2", qty=60, closestatus_title="正常")],
            "work_order": [dict(sourcebillnumber="B5", material_number="P1", taskstatus_title="开工")]}
    result = kit_rule([task("w", "B5", "2027-03-01", status="已确认")], rows, materials=MATERIALS, business_date=BD)[0]
    assert result["pass"] is True  # P1 has started; P2 alone (60) fits the 100 in stock


def test_batch_check_and_detail_agree_whatever_part_of_the_schedule_is_sent():
    network = [task("a", "B1", "2027-03-01"), task("b", "B2", "2027-03-05")]
    alone = kit_rule([network[1]], ROWS, materials=MATERIALS, business_date=BD, others=network)[0]
    table = kit_detail(network[1], network, ROWS, materials=MATERIALS, business_date=BD)
    assert (alone["pass"], alone["at"], alone["related"]) == (False, "2027-03-10", ["a"])
    assert table["at"] == alone["at"] and table["total"] == 1 and table["rows"][0]["id"] == "M1"
    moved = dict(network[0], start="2027-03-20T08:00:00+08:00")  # sent with the scenario's new start
    assert kit_rule([moved], ROWS, materials=MATERIALS, business_date=BD, others=network)[0]["pass"] is True
    assert kit_rule([network[1]], ROWS, materials=MATERIALS, business_date=BD, others=[moved, network[1]])[0]["pass"] is True


def test_confirmed_plans_turn_short_when_their_purchase_is_delayed():
    """The installed history: two confirmed U00-000080 plans rely on open PO 994-000328 due 3/11."""
    import csv
    from support_bkn_rows import DATA, csv_rows
    rows = {**csv_rows(), "forecast": list(csv.DictReader((DATA / "erp_mds_forecast.csv").open(encoding="utf-8"))),
            "work_order": list(csv.DictReader((DATA / "erp_production_work_order.csv").open(encoding="utf-8")))}
    materials = {r["material_code"]: r for r in csv.DictReader((DATA / "erp_material.csv").open(encoding="utf-8"))}
    plans = [{"key": p["plan_id"], "start": p["planned_start"], "resource": p["line_code"], "values": p}
             for p in csv.DictReader((DATA / "kit_schedule_plan.csv").open(encoding="utf-8"))]
    watched = [p for p in plans if p["values"]["product_code"] == "U00-000080" and p["values"]["plan_status"] == "已确认"
               and p["values"]["bill_no"] != "YCD2027020200000060" and "0060-" not in p["key"]]
    assert len(watched) == 2
    before = {r["key"]: r for r in kit_rule(plans, rows, materials=materials, business_date=BD)}
    assert all(before[p["key"]]["pass"] is True for p in watched)
    delayed = [dict(r, deliverdate="2027-06-30") if r["material_number"] == "994-000328" and r["deliverdate"] == "2027-03-11" else r
               for r in rows["purchase_order"]]
    after = {r["key"]: r for r in kit_rule(plans, {**rows, "purchase_order": delayed}, materials=materials, business_date=BD)}
    for plan in watched:
        assert (after[plan["key"]]["pass"], after[plan["key"]]["severity"], after[plan["key"]]["at"]) == (False, HARD, "2027-06-30")


def test_outside_an_interaction_the_rule_tools_read_through_the_ontology_query_api():
    from schedule_rules import line_check, tool_query
    fake = FakeObjectQuery()
    calls = []

    def refuse(**_):
        raise RuntimeError("conversation_required: bkn_context is required")

    def call(path, method="GET", body=None, headers=None):
        calls.append((path, method, headers))
        ot_id = path.rsplit("/", 1)[1]
        return fake(kn_id="kn", ot_id=ot_id, condition=body.get("condition"), limit=body["limit"], offset=body["offset"])
    tasks = [task("a", "YCD2026091600000057", "2027-03-08", product="382-000005", line="L-UR-AD")]
    assert line_check(tasks, tool_query(refuse, call))["results"][0]["pass"] is True
    assert calls and all(m == "POST" and h == {"X-HTTP-Method-Override": "GET"} for _, m, h in calls)
    assert calls[0][0].startswith("/api/ontology-query/v1/knowledge-networks/")


def test_other_reader_errors_are_not_hidden():
    from schedule_rules import tool_query

    def broken(**_):
        raise RuntimeError("object type not found")
    with pytest.raises(RuntimeError):
        tool_query(broken, lambda *a, **k: {})(kn_id="kn", ot_id="x", limit=1, offset=0)


def _run_bundled_line_check(monkeypatch, conversation):
    """The built line-check Function run as the sandbox runs it; returns its answer, the ``sandbox_sdk.bkn`` names it
    touched and the ontology-query calls it made."""
    fake, touched, rest = FakeObjectQuery(), [], []

    class Bkn(types.ModuleType):
        def __getattr__(self, name):  # the SDK sets itself up (and makes a workspace directory) on first access
            touched.append(name)
            return fake
    sdk = types.ModuleType("sandbox_sdk")
    sdk.bkn, sdk.tool = Bkn("sandbox_sdk.bkn"), (lambda fn: fn)

    def call(path, method="GET", body=None, headers=None):
        rest.append(path)
        return fake(kn_id="kn", ot_id=path.rsplit("/", 1)[1], condition=body.get("condition"), limit=body["limit"],
                    offset=body["offset"])
    osdk = types.ModuleType("bkn_osdk")
    osdk.call = call
    monkeypatch.setitem(sys.modules, "sandbox_sdk", sdk)
    monkeypatch.setitem(sys.modules, "bkn_osdk", osdk)
    for name in [m for m in sys.modules if m in ("fn", "managed_execution", "schedule_rules") or m.startswith("fn.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "path", list(sys.path))
    if conversation:
        monkeypatch.setenv("BKN_CONVERSATION_ID", conversation)
    else:
        monkeypatch.delenv("BKN_CONVERSATION_ID", raising=False)
    namespace: dict = {}
    exec(build_native_function_code(fixed_operation="line_check_rule"), namespace)
    tasks = [task("a", "YCD2026091600000057", "2027-03-08", product="382-000005", line="L-UR-AD")]
    return namespace["schedule_rule"](tasks=tasks, scenario={"edits": []}), touched, rest


def test_without_a_conversation_the_rule_function_never_touches_the_sdk(monkeypatch):
    # Each first touch of sandbox_sdk.bkn outside a conversation leaves a /workspace/adhoc-* directory, and the
    # sandbox walks all of them before and after every execution: rule checks went from ~1 s to 7-9 s.
    out, touched, rest = _run_bundled_line_check(monkeypatch, None)
    assert out["results"][0]["pass"] is True
    assert touched == []
    assert rest and all(p.startswith("/api/ontology-query/v1/knowledge-networks/") for p in rest)


def test_in_a_conversation_the_rule_function_reads_through_the_sdk(monkeypatch):
    out, touched, rest = _run_bundled_line_check(monkeypatch, "conv-1")
    assert out["results"][0]["pass"] is True
    assert set(touched) == {"query_object_instance"} and rest == []


def test_the_conversation_can_come_with_the_execution_event(monkeypatch):
    from schedule_rules import in_conversation
    monkeypatch.delenv("BKN_CONVERSATION_ID", raising=False)
    bkn = types.ModuleType("bkn")
    assert in_conversation(bkn) is False
    bkn._RUNTIME = {"bkn": {"conversation_id": "c"}}
    assert in_conversation(bkn) is True
    bkn._RUNTIME = {"bkn": {"conversation_id": " "}}
    assert in_conversation(bkn) is False


def test_a_date_outside_the_business_year_shows_its_year():
    from fn.kitrules import _short
    assert (_short("2027-03-10"), _short("2028-03-23")) == ("3/10", "2028/3/23")


def test_descriptions_shown_to_business_users_carry_no_calling_details():
    import re
    from function_catalog import KIT_PLAN_ACTIONS, KIT_SCHEDULE, RULE_USE, SCHEDULE_RULES
    texts = [KIT_SCHEDULE["description"], RULE_USE, *[s["description"] for s in SCHEDULE_RULES.values()],
             *[comment for _name, _kind, comment in KIT_PLAN_ACTIONS.values()]]
    for text in texts:
        assert not re.search(r"mode=|object_input|_instance|execute_|get_action|\btasks?\b", text), text


def test_demands_that_would_be_planned_are_checked_alone_in_a_batch_as_in_their_detail():
    """The demand view sends planned demands as their plans and the others as the plans they would make: those
    proposals must not take stock from each other, or a batch answer and the demand's detail disagree."""
    rows = {**ROWS, "forecast": ROWS["forecast"] + [dict(billno="B6", material_number="P2", qty=60, closestatus_title="正常")]}
    network = [task("a", "B1", "2027-03-01")]                      # takes 80 of the 100 in stock
    proposals = [task("+demand/x", "B2", "2027-03-02", product="P2"), task("+demand/y", "B6", "2027-03-03", product="P2")]
    batch = {r["key"]: r for r in kit_rule(network + proposals, rows, materials=MATERIALS, business_date=BD, others=network)}
    for proposal in proposals:
        table = kit_detail(proposal, network, rows, materials=MATERIALS, business_date=BD)
        alone = batch[proposal["key"]]
        assert (alone["pass"], alone["at"], alone["counts"][0]["value"]) == (False, table["at"], table["total"])
        assert table["rows"][0]["cells"]["short"] == 40                     # 60 needed, 20 left after plan a, not 0 after x
    assert batch["a"]["pass"] is True


def _plans_with(scenario, plans, demands):
    from schedule_rules import OT_FORECAST, OT_PLAN, _active_plans

    def read(ot_id, field=None, values=None):
        rows = plans if ot_id == OT_PLAN else demands if ot_id == OT_FORECAST else []
        return [r for r in rows if field is None or str(r.get(field)) in set(values or [])]
    return {t["key"]: t for t in _active_plans(read, scenario)}


def test_the_scenario_changes_every_check_works_with():
    plans = [dict(plan_id="KP-1", bill_no="B1", product_code="", line_code="L1", planned_start="2027-03-01",
                  planned_finish="2027-03-05", plan_status="已排"),
             dict(plan_id="KP-2", bill_no="B2", product_code="", line_code="L1", planned_start="2027-03-02",
                  planned_finish="2027-03-06", plan_status="已排")]
    demands = [dict(id="F-9", billno="B3", material_number="P3", qty=5, closestatus_title="正常")]
    scenario = {"edits": [
        {"source": "plans", "key": "KP-1", "operation": "adjust", "params": {"start": "2027-03-20", "end": "2027-03-24", "resource": "L2"}},
        {"source": "plans", "key": "KP-2", "operation": "cancel", "params": {"plan_status": "已取消"}},
        {"source": "demands", "key": "F-9", "operation": "create", "params": {"start": "2027-04-01", "end": "2027-04-03", "resource": "L3"}}]}
    found = _plans_with(scenario, plans, demands)
    assert set(found) == {"KP-1", "+demands/F-9"}                # the cancelled plan no longer counts
    assert (found["KP-1"]["start"], found["KP-1"]["resource"]) == ("2027-03-20", "L2")
    made = found["+demands/F-9"]
    assert (made["values"]["bill_no"], made["values"]["product_code"], made["start"], made["resource"]) == ("B3", "P3", "2027-04-01", "L3")


def test_a_task_without_a_line_is_not_applicable_for_the_line_check():
    lines = {"L1": {"line_name": "L1", "line_kind": "产线", "product_lines": "A"}}
    for resource in (None, ""):
        unplaced = dict(task("u", "B1", "2027-03-01"), resource=resource)
        result = line_rule([unplaced], forecasts=ROWS["forecast"], lines=lines, product_lines={"P1": "A"})[0]
        assert (result["key"], result["pass"], result["text"]) == ("u", None, "")

