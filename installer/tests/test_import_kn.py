import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "samples/supply_ontology_hand/tools/import_kn.py"
_SPEC = importlib.util.spec_from_file_location("import_kn", _PATH)
IMPORT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(IMPORT)


class ImportKnTest(unittest.TestCase):
    def test_import_keeps_ownership_within_native_tag_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "kn.json"
            original = {"id": "sample", "name": "Sample", "tags": ["a", "b", "c"]}
            source.write_text(json.dumps(original), encoding="utf-8")
            posted = []

            def run_cmd(args):
                if args[2] == "call":
                    posted.append(json.loads(args[-1]))
                    return "{}"
                if posted:
                    return json.dumps(posted[0])
                raise RuntimeError("not found")

            required = ["bkn-samples", "bkn-sample-supply-chain", "bkn-samples-version-0-1-0"]
            with patch.object(IMPORT, "run_cmd", run_cmd), patch.dict(
                os.environ, {"BKN_SAMPLE_OWNERSHIP_TAGS": ",".join(required)}
            ):
                report = IMPORT.import_kn(source)
            self.assertEqual(posted[0]["tags"], ["a", "b", *required])
            self.assertEqual(report["omitted_descriptive_tags"], ["c"])
            self.assertEqual(json.loads(source.read_text(encoding="utf-8")), original)

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

    def test_stops_when_an_existing_network_has_no_installer_claim(self):
        directory = Path(tempfile.mkdtemp())
        source = directory / "kn.json"
        source.write_text(json.dumps({"id": "supply_ontology_hand", "name": "供应链本体知识网络-手工版", "tags": ["体验版"]}), encoding="utf-8")

        def run_cmd(args):
            if args[2:4] == ["bkn", "get"]:
                return json.dumps({"id": "supply_ontology_hand", "name": "供应链本体知识网络-手工版", "tags": ["体验版"]})
            raise AssertionError(args)

        IMPORT.run_cmd = run_cmd
        previous = os.environ.get("BKN_SAMPLE_OWNERSHIP_TAGS")
        os.environ["BKN_SAMPLE_OWNERSHIP_TAGS"] = "bkn-samples,bkn-sample-supply-chain,bkn-samples-version-0-1-0"
        try:
            with self.assertRaises(IMPORT.OwnershipConflict):
                IMPORT.import_kn(source)
        finally:
            if previous is None:
                os.environ.pop("BKN_SAMPLE_OWNERSHIP_TAGS", None)
            else:
                os.environ["BKN_SAMPLE_OWNERSHIP_TAGS"] = previous


if __name__ == "__main__":
    unittest.main()
