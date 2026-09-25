import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "samples/supply_ontology_hand/tools/import_kn.py"
_SPEC = importlib.util.spec_from_file_location("import_kn", _PATH)
IMPORT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(IMPORT)


class ImportKnTest(unittest.TestCase):
    def test_reuses_an_existing_network_without_posting(self):
        directory = Path(tempfile.mkdtemp())
        source = directory / "kn.json"
        source.write_text(
            json.dumps({"id": "supply_ontology_hand", "name": "供应链本体知识网络-手工版"}),
            encoding="utf-8",
        )
        calls = []

        def run_cmd(args):
            calls.append(args)
            if args[2:4] == ["bkn", "get"]:
                return json.dumps({"id": "supply_ontology_hand", "name": "供应链本体知识网络-手工版"})
            raise AssertionError(args)

        IMPORT.run_cmd = run_cmd
        report = IMPORT.import_kn(source)
        self.assertEqual(report["action"], "reuse")
        self.assertTrue(all(call[2] != "call" for call in calls))

    def test_stops_when_the_existing_name_differs(self):
        directory = Path(tempfile.mkdtemp())
        source = directory / "kn.json"
        source.write_text(json.dumps({"id": "supply_ontology_hand", "name": "供应链本体知识网络-手工版"}), encoding="utf-8")

        def run_cmd(args):
            if args[2:4] == ["bkn", "get"]:
                return json.dumps({"id": "supply_ontology_hand", "name": "other"})
            raise AssertionError(args)

        IMPORT.run_cmd = run_cmd
        with self.assertRaises(RuntimeError):
            IMPORT.import_kn(source)


if __name__ == "__main__":
    unittest.main()
