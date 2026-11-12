"""Machine-scheduling rule functions, runtime and registration of both manufacturing samples."""
import csv
import importlib
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLES = {"zh": REPO / "samples/manufacturing-industry-zh-cn", "en": REPO / "samples/manufacturing-industry-en-us"}
KN = {"zh": "manufacturing_industry_zh_cn", "en": "manufacturing_industry_en_us"}
SHARED = ("machine_schedule.py", "schedule_runtime.py", "function_bundle.py", "register_capabilities.py")


def modules(lang):
    tools = str(SAMPLES[lang] / "tools")
    for name in ("machine_schedule", "schedule_runtime", "function_bundle", "register_capabilities", "ownership_receipt"):
        sys.modules.pop(name, None)
    sys.path.insert(0, tools)
    try:
        return {name: importlib.import_module(name) for name in ("machine_schedule", "schedule_runtime", "function_bundle", "register_capabilities")}
    finally:
        sys.path.remove(tools)


def tables(lang):
    out = {}
    for path in sorted((SAMPLES[lang] / "data").glob("*.csv")):
        with path.open(encoding="utf-8") as handle:
            out[path.stem] = list(csv.DictReader(handle))
    return out


def by_key(answer):
    return {r["key"]: r for r in answer["results"]}


class Base(unittest.TestCase):
    lang = "zh"

    @classmethod
    def setUpClass(cls):
        cls.m = modules(cls.lang)
        cls.ms = cls.m["machine_schedule"]
        cls.t = tables(cls.lang)

    def check(self, rule, tasks, scenario=None, **kw):
        return by_key(self.ms.check(rule, self.t, tasks, scenario, language=self.lang, **kw))


class SharedCodeTest(unittest.TestCase):
    def test_both_samples_carry_the_same_code(self):
        for name in SHARED + ("../db/database.py", "../platform/sample_platform.py"):
            self.assertEqual((SAMPLES["zh"] / "tools" / name).read_bytes(), (SAMPLES["en"] / "tools" / name).read_bytes(), name)

    def test_pre_schedule_matches_the_data_story(self):
        for lang in SAMPLES:
            ops = {r["operation_id"]: r for r in tables(lang)["manufacturing_operations"]}
            self.assertEqual(ops["OP-2703-09-10"]["planned_machine_id"], "MACH-MILL-04")
            self.assertEqual(ops["OP-2703-06-20"]["predecessor_operation_id"], "OP-2703-06-10")
            self.assertEqual(ops["OP-2703-06-10"]["predecessor_operation_id"], "")
            done = [r for r in ops.values() if r["status"] in ("已完成", "completed")]
            self.assertTrue(all(r["planned_start_date"] <= r["planned_end_date"] for r in ops.values()))
            self.assertEqual(len(done), 105)


class KitTest(Base):
    def test_kit_on_the_stored_schedule(self):
        r = self.check("work_order_kit", [])
        self.assertFalse(r["OP-2702-03-10"]["pass"])
        self.assertEqual(r["OP-2702-03-10"]["severity"], "hard")
        self.assertEqual(r["OP-2702-03-10"]["at"], "2027-03-02")
        self.assertTrue(r["OP-2702-03-10"]["detail"])
        self.assertIn("OP-2703-04-10", r["OP-2702-03-10"]["related"])     # competes for stainless bar
        self.assertFalse(r["OP-2703-02-10"]["pass"])                      # draft BOM
        self.assertIn("BOMV-FL150-B", r["OP-2703-02-10"]["text"])
        self.assertTrue(r["OP-2703-04-10"]["pass"])
        self.assertIsNone(r["OP-2703-04-20"]["pass"])                     # kit is checked on the first open operation
        self.assertLessEqual(len(r["OP-2702-03-10"]["counts"]), 4)

    def test_competition_moves_the_shortage_to_the_later_order(self):
        moved = self.check("work_order_kit", [{"key": "OP-2702-03-10", "start": "2027-03-02", "end": "2027-03-03"},
                                              {"key": "OP-2703-08-10"}])
        self.assertTrue(moved["OP-2702-03-10"]["pass"])                   # now draws the 03-02 arrival first
        before = self.check("work_order_kit", [{"key": "OP-2703-08-10"}])
        short = lambda text: int("".join(c for c in text.split("：" if self.lang == "zh" else "key: ")[-1].split("，" if self.lang == "zh" else ";")[0] if c.isdigit()))
        self.assertGreater(short(moved["OP-2703-08-10"]["text"]), short(before["OP-2703-08-10"]["text"]))

    def test_scenario_edits_move_operations_not_sent(self):
        edits = {"edits": [{"source": "manufacturing_operations", "key": "OP-2702-03-10", "operation": "modify",
                            "params": {"planned_start_date": "2027-03-02", "planned_end_date": "2027-03-03"}}]}
        self.assertTrue(self.check("work_order_kit", [{"key": "OP-2702-03-10"}], edits)["OP-2702-03-10"]["pass"])

    def test_detail_pages_filters_and_searches(self):
        ms = self.ms
        whole = ms.detail("work_order_kit", self.t, {"key": "OP-2703-02-10"}, language=self.lang)
        self.assertEqual(whole["total"], 2)
        self.assertEqual(whole["rows"][0]["id"], "RM-AL6061")             # the shortage first
        self.assertTrue(whole["rows"][0]["key"])
        self.assertEqual({c["key"] for c in whole["columns"]} >= {"material", "short", "ready", "source"}, True)
        page = ms.detail("work_order_kit", self.t, {"key": "OP-2703-02-10"}, language=self.lang, query={"offset": 1, "limit": 1})
        self.assertEqual((page["total"], [r["id"] for r in page["rows"]]), (2, ["PC-BOLT"]))
        keyed = ms.detail("work_order_kit", self.t, {"key": "OP-2703-02-10"}, language=self.lang, query={"keyOnly": True})
        self.assertEqual([r["id"] for r in keyed["rows"]], ["RM-AL6061"])
        grouped = ms.detail("work_order_kit", self.t, {"key": "OP-2703-02-10"}, language=self.lang, query={"group": "ok"})
        self.assertEqual([r["id"] for r in grouped["rows"]], ["PC-BOLT"])
        found = ms.detail("work_order_kit", self.t, {"key": "OP-2703-02-10"}, language=self.lang, query={"search": "bolt"})
        self.assertEqual(found["total"], 1)
        po = ms.detail("work_order_kit", self.t, {"key": "OP-2703-02-10"}, language=self.lang)["rows"][1]
        self.assertEqual(po["links"]["source"], {"objectType": "purchase_orders", "key": "PO-2703-BOLT"})
        late = ms.detail("work_order_kit", self.t, {"key": "OP-2702-03-10"}, language=self.lang)
        self.assertEqual(late["at"], "2027-03-02")
        self.assertEqual(late["rows"][0]["group"], "late_po")

    def test_detail_of_a_task_the_rule_does_not_cover(self):
        na = self.ms.detail("work_order_kit", self.t, {"key": "OP-2703-04-20"}, language=self.lang)
        self.assertEqual((na["total"], na["rows"]), (0, []))


class CapabilityTest(Base):
    def test_suspended_capability_is_hard_and_a_qualified_machine_passes(self):
        r = self.check("machine_capability", [{"key": "OP-2703-09-10"}, {"key": "OP-2703-06-10", "resource": "MACH-MILL-04"},
                                              {"key": "OP-2703-08-20", "resource": "MACH-MILL-02"}])
        self.assertEqual((r["OP-2703-09-10"]["pass"], r["OP-2703-09-10"]["severity"]), (False, "hard"))
        self.assertFalse(r["OP-2703-06-10"]["pass"])
        self.assertTrue(r["OP-2703-08-20"]["pass"])
        wrong = self.check("machine_capability", [{"key": "OP-2703-08-10", "resource": "MACH-MILL-01"}])["OP-2703-08-10"]
        self.assertFalse(wrong["pass"])                                    # a lathe operation on a mill: no turning capability

    def test_detail_lists_the_machines_with_the_capability(self):
        d = self.ms.detail("machine_capability", self.t, {"key": "OP-2703-09-10"}, language=self.lang)
        self.assertEqual(d["rows"][0]["id"], "MACH-MILL-04")
        self.assertEqual({g["id"] for g in d["groups"]}, {"qualified", "suspended"})


class OperatorTest(Base):
    def test_no_qualified_operator_in_the_week_is_hard(self):
        r = self.check("operator_shift", [{"key": "OP-2703-09-20"}, {"key": "OP-2703-11-20"}])
        self.assertEqual((r["OP-2703-09-20"]["pass"], r["OP-2703-09-20"]["severity"]), (False, "hard"))
        self.assertTrue(r["OP-2703-11-20"]["pass"])
        moved = self.check("operator_shift", [{"key": "OP-2703-09-20", "start": "2027-03-22", "end": "2027-03-23"}])
        self.assertTrue(moved["OP-2703-09-20"]["pass"])

    def test_fewer_operators_than_parallel_operations_is_soft(self):
        r = self.check("operator_shift", [{"key": "OP-2703-05-20"}])["OP-2703-05-20"]
        self.assertEqual((r["pass"], r["severity"], r["related"]), (False, "soft", ["OP-2703-07-20"]))

    def test_detail_names_the_operators(self):
        d = self.ms.detail("operator_shift", self.t, {"key": "OP-2703-09-20"}, language=self.lang)
        groups = {r["id"]: r["group"] for r in d["rows"]}
        self.assertEqual(groups["OPR-07"], "unqualified")
        self.assertEqual(groups["OPR-06"], "not_assigned")


class ChangeoverTest(Base):
    def test_different_setup_class_after_the_previous_operation_is_soft(self):
        r = self.check("changeover", [{"key": "OP-2703-05-10"}, {"key": "OP-2703-10-20"}])
        self.assertEqual((r["OP-2703-05-10"]["pass"], r["OP-2703-05-10"]["severity"]), (False, "soft"))
        self.assertIn("OP-2703-04-20", r["OP-2703-05-10"]["related"])
        self.assertTrue(r["OP-2703-10-20"]["pass"])


class ContractTest(Base):
    def test_failure_paths_raise_so_tasks_are_not_checked(self):
        ms = self.ms
        with self.assertRaises(ms.CannotCheck):
            ms.check("changeover", self.t, {"key": "x"}, language=self.lang)
        with self.assertRaises(ms.CannotCheck):
            ms.check("changeover", self.t, [{"key": "OP-2703-05-10"}] * 201, language=self.lang)
        with self.assertRaises(ms.CannotCheck):
            ms.check("changeover", self.t, [{"key": "OP-2703-05-10", "start": "March"}], language=self.lang)
        with self.assertRaises(ms.CannotCheck):
            ms.check("changeover", self.t, [{"key": "OP-2703-05-10", "start": "2027-03-09", "end": "2027-03-08"}], language=self.lang)
        with self.assertRaises(ms.CannotCheck):
            ms.check("unknown", self.t, [], language=self.lang)
        with self.assertRaises(ms.CannotCheck):
            ms.detail("changeover", self.t, None, language=self.lang)

    def test_completed_running_and_unknown_tasks_are_not_applicable(self):
        r = self.check("machine_capability", [{"key": "OP-2611-01-10"}, {"key": "OP-2703-03-10"}, {"key": "MWO-036"}])
        self.assertEqual([r[k]["pass"] for k in ("OP-2611-01-10", "OP-2703-03-10", "MWO-036")], [None, None, None])
        self.assertNotIn("severity", r["MWO-036"])

    def test_workshop_instants_are_read_on_the_plant_clock(self):
        # 03-22..03-23 sent from a +08:00 page: start 03-22 00:00, end (exclusive) 03-24 00:00.
        f = self.ms.Facts(self.t, language=self.lang)
        f.take({"key": "OP-2703-09-20", "start": "2027-03-21T16:00:00.000Z", "end": "2027-03-23T16:00:00.000Z", "values": {}})
        self.assertEqual(f.plan["OP-2703-09-20"][1:], ("2027-03-22", "2027-03-23"))
        f.take({"key": "OP-2703-09-20", "start": "2027-03-21T16:00:00.000Z", "end": "2027-03-23T16:00:00.000Z",
                 "values": {"planned_start_date": "2027-03-25", "planned_end_date": "2027-03-26"}})
        self.assertEqual(f.plan["OP-2703-09-20"][1:], ("2027-03-25", "2027-03-26"))

    def test_labels_follow_the_locale(self):
        zh = self.check("machine_capability", [{"key": "OP-2703-09-10"}], locale="zh-CN")["OP-2703-09-10"]["text"]
        en = self.check("machine_capability", [{"key": "OP-2703-09-10"}], locale="en-US")["OP-2703-09-10"]["text"]
        self.assertIn("能力", zh)
        self.assertIn("suspended" if self.lang == "en" else "暂停", en)
        self.assertNotIn("能力", en)


class AdjustTest(Base):
    def test_adjust_operation(self):
        f = self.ms.Facts(self.t, language=self.lang)
        out = self.ms.adjust_operation(f, {"operation_id": "OP-2703-09-10", "planned_machine_id": "MACH-MILL-02",
                                           "planned_start_date": "2027-03-15"})
        self.assertEqual((out["row"]["planned_machine_id"], out["row"]["planned_start_date"], out["row"]["planned_end_date"]),
                         ("MACH-MILL-02", "2027-03-15", "2027-03-16"))
        self.assertEqual(out["previous"]["planned_machine_id"], "MACH-MILL-04")
        for bad in ({"operation_id": "OP-2611-01-10", "planned_start_date": "2027-03-15"},
                    {"operation_id": "OP-2703-09-10", "planned_machine_id": "MACH-TURN-01"},
                    {"operation_id": "OP-2703-09-10", "planned_start_date": "2027-03-15", "planned_end_date": "2027-03-14"},
                    {"operation_id": "OP-404"}):
            with self.assertRaises(self.ms.CannotCheck, msg=bad):
                self.ms.adjust_operation(f, bad)
        with self.assertRaises(self.ms.CannotCheck) as refused:
            self.ms.adjust_operation(f, {"operation_id": "OP-2703-09-10", "planned_machine_id": "MACH-TURN-01"})
        self.assertIn("不属于" if self.lang == "zh" else "is not in", str(refused.exception))

    def test_adjust_maintenance_keeps_the_due_day(self):
        rows = self.t["maintenance_work_orders"]
        out = self.ms.adjust_maintenance(rows, {"maintenance_work_order_id": "MWO-036", "planned_start_date": "2027-03-10"})
        self.assertEqual((out["row"]["planned_start_date"], out["row"]["planned_end_date"], out["row"]["planned_date"]),
                         ("2027-03-10", "2027-03-10", "2027-03-07"))
        with self.assertRaises(self.ms.CannotCheck):
            self.ms.adjust_maintenance(rows, {"maintenance_work_order_id": "MWO-001", "planned_start_date": "2027-03-10"})


class RuntimeTest(Base):
    def query(self, calls=None):
        def query(kn_id, ot_id, limit, offset, condition=None):
            if calls is not None:
                calls.append((ot_id, offset))
            rows = self.t[ot_id]
            return {"datas": rows[offset:offset + limit], "total_count": len(rows)}
        return query

    def test_rule_reads_every_page_and_answers(self):
        rt = self.m["schedule_runtime"]
        rt.KN_ID, rt.LANGUAGE, rt.PAGE_SIZE = KN[self.lang], self.lang, 50
        calls = []
        out = rt.rule("work_order_kit", self.query(calls), tasks=[{"key": "OP-2703-02-10"}])
        self.assertFalse(out["results"][0]["pass"])
        self.assertIn(("manufacturing_operations", 100), calls)
        d = rt.rule("work_order_kit", self.query(), mode="detail", task={"key": "OP-2703-02-10"}, detail_query={"limit": 1})
        self.assertEqual((d["total"], len(d["rows"])), (2, 1))

    def test_without_an_interaction_the_rule_reads_ontology_query_directly(self):
        rt = self.m["schedule_runtime"]
        rt.KN_ID, rt.LANGUAGE, rt.PAGE_SIZE = KN[self.lang], self.lang, 500
        sdk_calls, rest_calls = [], []

        def sdk(**kw):
            sdk_calls.append(kw["ot_id"])
            raise RuntimeError('query_object_instance: {"error":{"code":"conversation_required","message":"bkn_context is required"}}')

        def call(path, method="GET", body=None, headers=None):
            table = path.rsplit("/", 1)[1]
            rest_calls.append((table, body["offset"], headers))
            rows = self.t[table]
            return {"datas": rows[body["offset"]:body["offset"] + body["limit"]], "total_count": len(rows)}
        out = rt.rule("machine_capability", sdk, call=call, tasks=[{"key": "OP-2703-09-10"}])
        self.assertFalse(out["results"][0]["pass"])
        self.assertEqual(len(sdk_calls), 1)                                # decided once per call
        self.assertEqual(rest_calls[0][2], {"X-HTTP-Method-Override": "GET"})
        with self.assertRaises(RuntimeError):                              # other SDK failures stay failures
            rt.rule("changeover", lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")), call=call, tasks=[])

    def test_partial_reads_fail(self):
        rt = self.m["schedule_runtime"]
        with self.assertRaises(ValueError):
            rt.read_table(lambda **kw: {"datas": [{"a": 1}], "total_count": 5}, "x")
        with self.assertRaises(ValueError):
            rt.read_table(lambda **kw: {"datas": [], "status": "partial"}, "x")

    def test_adjust_writes_the_typed_row_to_the_dataset(self):
        rt = self.m["schedule_runtime"]
        rt.KN_ID, rt.LANGUAGE = KN[self.lang], self.lang
        rt.FIELDS = self.m["function_bundle"].settings()["fields"]
        sent = []

        def call(path, method="GET", body=None):
            if method == "GET":
                return {"entries": [{"data_source": {"type": "resource", "id": "ds-1"}}]}
            sent.append((path, body))
            return {"entries": [{"id": body["entries"][0]["_id"], "status": 200}]}
        out = rt.adjust_operation(self.query(), call, {"operation_id": "OP-2703-09-10", "planned_machine_id": "MACH-MILL-02",
                                                        "planned_start_date": "2027-03-15", "planned_end_date": "2027-03-16"})
        path, body = sent[0]
        self.assertEqual(path, "/api/vega-backend/v1/resources/ds-1/data")
        doc = body["entries"][0]
        self.assertEqual((doc["_id"], doc["planned_machine_id"], doc["sequence_number"], doc["standard_duration_days"]),
                         ("OP-2703-09-10", "MACH-MILL-02", 10, 2))
        self.assertEqual(out["operation"]["planned_end_date"], "2027-03-16")
        with self.assertRaises(ValueError):
            rt.adjust_maintenance(self.query(), lambda *a, **k: {"entries": [{"status": 500}]} if k.get("method") == "PUT" else
                                  {"data_source": {"type": "resource", "id": "ds-2"}},
                                  {"maintenance_work_order_id": "MWO-036", "planned_start_date": "2027-03-10"})


class RegistrationTest(Base):
    def test_functions_compile_and_actions_follow_the_fields(self):
        reg, bundle = self.m["register_capabilities"], self.m["function_bundle"]
        zh = self.lang == "zh"
        for op in reg.OPERATIONS:
            compile(bundle.build(op, KN[self.lang]), op, "exec")
        actions = {a["id"].removeprefix(KN[self.lang] + "_"): a for a in reg.action_definitions(KN[self.lang], "box", {o: "t-" + o for o in reg.OPERATIONS}, zh)}
        self.assertEqual(len(actions), 6)
        adjust = actions["adjust_operation_schedule"]
        self.assertEqual((adjust["operation_config"], adjust["object_type_id"], adjust["action_type"]),
                         ({"type": "object"}, "manufacturing_operations", "modify"))
        self.assertEqual([(p["name"], p["value_from"]) for p in adjust["parameters"]],
                         [("operation_id", "property"), ("planned_machine_id", "input"), ("planned_start_date", "input"), ("planned_end_date", "input")])
        self.assertEqual(adjust["name"], "调整工序排程" if zh else "Adjust operation schedule")
        mwo = actions["adjust_maintenance_work_order"]
        self.assertEqual(mwo["name"], "调整维修工单" if zh else "Adjust maintenance work order")
        self.assertEqual([p["name"] for p in mwo["parameters"]], ["maintenance_work_order_id", "planned_start_date", "planned_end_date"])
        rule = actions["work_order_kit_rule"]
        self.assertEqual((rule["operation_config"], rule["object_type_id"], [p["name"] for p in rule["parameters"]]),
                         ({"type": "tool"}, "", ["tasks"]))
        fields = self.m["function_bundle"].settings()["fields"]
        for name in ("planned_machine_id", "planned_start_date", "planned_end_date"):
            self.assertIn(name, fields["manufacturing_operations"])

    def test_install_then_verify(self):
        reg = self.m["register_capabilities"]
        reg.remember = lambda *a: None
        reg.require_owned = lambda *a: None
        state = {"datasets": [], "tools": [], "actions": [], "bound": {}, "loaded": {}}

        def cli(*args):
            if args[:3] == ("vega", "catalog", "resources"):
                return {"entries": [{"name": n, "id": "ds-" + n} for n in state["datasets"]]}
            if args[0] == "call" and args[1].endswith("/resources") and args[3] == "POST":
                body = json.loads(args[5]); state["datasets"].append(body["name"]); return {"id": "ds-" + body["name"]}
            if args[0] == "call" and "/data" in args[1]:
                rows = json.loads(args[5])["entries"]; state["loaded"][args[1]] = len(rows)
                return {"entries": [{"id": r["_id"], "status": 200} for r in rows]}
            if args[:2] == ("bkn", "object-type") and args[2] == "get":
                return {"entries": [{"id": args[4], "data_source": {"type": "resource", "id": state["bound"].get(args[4])}}]}
            if args[:2] == ("bkn", "object-type") and args[2] == "update":
                body = json.loads(Path(args[6]).read_text()); state["bound"][args[4]] = body["data_source"]["id"]; return {}
            if args[:2] == ("toolbox", "list"):
                return {"data": [{"box_name": reg.box_name(), "box_id": "box", "status": "published"}] if state["tools"] else []}
            if args[0] == "call" and args[1].endswith("/tool-box"):
                return {"box_id": "box"}
            if args[0] == "call" and args[1].endswith("/tool"):
                body = json.loads(args[5])["function_input"]; state["tools"].append(body); return {"success_ids": ["t-" + body["name"]]}
            if args[:2] == ("tool", "list"):
                return {"tools": [{"name": t["name"], "tool_id": "t-" + t["name"]} for t in state["tools"]]}
            if args[:2] == ("tool", "get"):
                op = args[-1].removeprefix("t-")
                return {"metadata": {"function_content": {"code": next(t["code"] for t in state["tools"] if t["name"] == op)}}}
            if args[0] == "call" and "/action-types" in args[1]:
                state["actions"] = json.loads(args[5])["entries"]; return {}
            if args[:2] == ("bkn", "action-type"):
                return {"entries": state["actions"]}
            return {}
        out = reg.run(cli, KN[self.lang], apply=True, catalog_id="cat")
        self.assertEqual(set(out["datasets"]), {"manufacturing_operations", "maintenance_work_orders"})
        self.assertEqual(sorted(state["loaded"].values()), [45, 136])
        self.assertEqual(len(state["tools"]), 6)
        self.assertEqual(len(out["action_ids"]), 6)
        verified = reg.run(cli, KN[self.lang], apply=False, catalog_id="cat")
        self.assertEqual(verified["tool_ids"], out["tool_ids"])
        state["actions"] = state["actions"][:-1]
        with self.assertRaises(ValueError):
            reg.run(cli, KN[self.lang], apply=False, catalog_id="cat")


def english(cls):
    return type(cls.__name__ + "English", (cls,), {"lang": "en"})


for _case in (KitTest, CapabilityTest, OperatorTest, ChangeoverTest, ContractTest, AdjustTest, RuntimeTest, RegistrationTest):
    globals()[_case.__name__ + "English"] = english(_case)


if __name__ == "__main__":
    unittest.main()
