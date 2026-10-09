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
            components={"functions": True, "skills": True},
            run_cli=_cli(
                {
                    ("toolbox", "list"): {"data": []},
                    ("skill", "list"): {"data": []},
                }
            ),
        )
        by_name = {item["name"]: item["ok"] for item in checks}
        self.assertTrue(by_name["tables-discovered"])
        self.assertFalse(by_name["capability-callable"])
        self.assertFalse(by_name["skill-discoverable"])

    def test_enabled_tool_and_published_skills_pass(self):
        import sys

        sys.path.insert(0, str(VERIFY.SAMPLE_DIR / "tools"))
        from register_skills import local_skills

        names = [{"name": name, "status": "published"} for name, _path in local_skills()]
        checks = VERIFY.build_checks(
            data_ok=True,
            components={"functions": True, "skills": True},
            run_cli=_cli(
                {
                    ("toolbox", "list"): {"data": [{"box_name": VERIFY.BOX_NAME, "box_id": "box-1"}]},
                    ("tool", "list"): {"tools": [{"name": "bom_list", "status": "enabled"}]},
                    ("skill", "list"): {"data": names},
                }
            ),
        )
        self.assertTrue(all(item["ok"] for item in checks))

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
