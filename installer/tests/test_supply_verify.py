import importlib.util
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "samples/supply_ontology_hand/platform/verify_platform.py"
_SPEC = importlib.util.spec_from_file_location("verify_platform", _PATH)
VERIFY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(VERIFY)


def _cli(answers: dict):
    def run(args):
        key = tuple(args[:2])
        if key not in answers:
            raise AssertionError(args)
        return answers[key]

    return run


class SupplyVerifyTest(unittest.TestCase):
    def test_data_smoke_does_not_mark_capabilities_ready(self):
        checks = VERIFY.build_checks(
            data_ok=True,
            components={"functions": True, "skills": False},
            run_cli=_cli(
                {
                    ("toolbox", "list"): {"data": []},
                }
            ),
        )
        by_name = {item["name"]: item["ok"] for item in checks}
        self.assertTrue(by_name["tables-discovered"])
        self.assertFalse(by_name["capability-callable"])
        self.assertNotIn("skill-discoverable", by_name)

    def test_enabled_tool_that_reads_the_network_passes(self):
        import sys

        sys.path.insert(0, str(VERIFY.SAMPLE_DIR / "tools"))
        from function_catalog import FUNCTION_CATALOG

        tools = [{"name": spec["name"], "tool_id": operation, "status": "enabled"} for operation, spec in FUNCTION_CATALOG.items()]
        bindings = [{"capability_type": "function", "box_id": "box-1", "capability_id": operation} for operation in FUNCTION_CATALOG]
        checks = VERIFY.build_checks(
            data_ok=True,
            components={"functions": True, "skills": False},
            run_cli=_cli(
                {
                    ("toolbox", "list"): {"data": [{"box_name": VERIFY.BOX_NAME, "box_id": "box-1"}]},
                    ("tool", "list"): {"tools": tools},
                    ("bkn", "capability"): {"entries": bindings},
                    ("tool", "execute"): {"status_code": 200, "body": {"result": {"leadtime_days": 14}}},
                }
            ),
        )
        self.assertTrue(all(item["ok"] for item in checks))

    def test_mounted_functions_that_cannot_read_the_network_fail(self):
        import sys
        sys.path.insert(0, str(VERIFY.SAMPLE_DIR / "tools"))
        from function_catalog import FUNCTION_CATALOG
        calls = []
        answers = {
            ("toolbox", "list"): {"data": [{"box_name": VERIFY.BOX_NAME, "box_id": "box-1"}]},
            ("tool", "list"): {"tools": [{"name": spec["name"], "tool_id": operation, "status": "enabled"}
                                             for operation, spec in FUNCTION_CATALOG.items()]},
            ("bkn", "capability"): {"entries": [{"capability_type": "function", "box_id": "box-1", "capability_id": operation}
                                                 for operation in FUNCTION_CATALOG]},
            # What the runtime returns when the function's BKN read is refused.
            ("tool", "execute"): {"status_code": 200, "body": {"result": None, "stderr": "ToolError: conversation_required"}},
        }

        def run(args):
            calls.append(args)
            return answers[tuple(args[:2])]

        self.assertFalse(VERIFY.capability_ready(run))
        execute = next(args for args in calls if args[:2] == ["tool", "execute"])
        self.assertEqual(execute[2], "leadtime_days")

    def test_published_tools_without_network_bindings_fail(self):
        import sys
        sys.path.insert(0, str(VERIFY.SAMPLE_DIR / "tools"))
        from function_catalog import FUNCTION_CATALOG
        run = _cli({
            ("toolbox", "list"): {"data": [{"box_name": VERIFY.BOX_NAME, "box_id": "box-1"}]},
            ("tool", "list"): {"tools": [{"name": spec["name"], "tool_id": operation, "status": "enabled"}
                                             for operation, spec in FUNCTION_CATALOG.items()]},
            ("bkn", "capability"): {"entries": []},
        })
        self.assertFalse(VERIFY.capability_ready(run))

    def test_forecast_metric_expectations_match_locked_csv(self):
        import csv
        import json
        from decimal import Decimal

        with (VERIFY.SAMPLE_DIR / "data/erp_mds_forecast.csv").open() as source:
            rows = list(csv.DictReader(source))
        cases = {case["id"]: case for case in json.loads(
            (VERIFY.SAMPLE_DIR / "tools/assets/metrics-query-examples.json").read_text())["cases"]}
        self.assertEqual(sum(Decimal(row["qty"]) for row in rows),
                         cases["forecast_qty_all"]["expected_value"])
        self.assertEqual(sum(row["closestatus_title"] != "已关闭" for row in rows),
                         cases["open_forecast_count"]["expected_value"])
        definitions = json.loads((VERIFY.SAMPLE_DIR / "tools/assets/metrics-create.json").read_text())
        metric = next(item for item in definitions["entries"] if item["name"] == "未关闭预测单数")
        self.assertIn("closestatus_title", [item["name"] for item in metric["analysis_dimensions"]])

    def test_metric_queries_and_bindings_must_both_pass(self):
        report = {key: {"passed": [{"id": "metric"}], "failed": []}
                  for key in ("verify_metrics", "verify_logic_properties")}
        self.assertTrue(all(item["ok"] for item in VERIFY.metric_checks(report, True)))
        self.assertFalse(any(item["ok"] for item in VERIFY.metric_checks(report, False)))
        report["verify_metrics"]["failed"] = [{"actual": 0}]
        checks = VERIFY.metric_checks(report, True)
        self.assertFalse(checks[0]["ok"])
        self.assertTrue(checks[1]["ok"])
        self.assertFalse(any(item["ok"] for item in VERIFY.metric_checks({}, True)))

    def test_absent_functions_and_skills_are_not_required(self):
        calls = []

        def run(args):
            calls.append(args)
            raise AssertionError(args)

        checks = VERIFY.build_checks(data_ok=True, components={"functions": False, "skills": False}, run_cli=run)
        self.assertEqual([item["name"] for item in checks], list(VERIFY.DATA_CHECKS))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
