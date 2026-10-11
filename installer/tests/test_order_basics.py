import importlib.util
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / "samples/order-basics"


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class OrderBasicsTest(unittest.TestCase):
    def test_import_uses_standard_api_and_queries_real_objects(self):
        network = module("order_network_cli", "platform/network.py")
        calls = []
        def command(*args):
            calls.append(args)
            if args[:3] == ("vega", "resource", "list"):
                return {"entries": [{"id": name + "-resource", "name": "order_basics." + name}
                                    for name in ("products", "orders")]}
            if args[0] == "call":
                body = json.loads(args[-1])
                self.assertEqual(args[:5], ("call", "-X", "POST", "/api/ontology-manager/v1/knowledge-networks", "-d"))
                self.assertEqual(body["object_types"][0]["data_source"]["id"], "products-resource")
                return {"id": "order_basics"}
            if args[:3] == ("bkn", "object-type", "query"):
                database = module("order_fixture_cli", "db/database.py")
                return {"datas": database.fixture()[0][args[4] + ".csv"]}
            if args == ("bkn", "get", "order_basics", "--export"):
                return json.loads((ROOT / "kn/order_basics.json").read_text())
            self.fail("unexpected CLI command: " + repr(args))
        with tempfile.TemporaryDirectory() as directory:
            input_path, output_path = Path(directory) / "input.json", Path(directory) / "output.json"
            input_path.write_text(json.dumps({"sample": "order-basics", "version": "0.1.0",
                "knowledgeNetwork": {"id": "order_basics"}, "database": {"name": "order_basics"},
                "catalog": {"id": "catalog-id"}}))
            with patch.dict(os.environ, {"BKN_SAMPLE_INPUT": str(input_path), "BKN_SAMPLE_OUTPUT": str(output_path)}), \
                 patch.object(network, "cli", side_effect=command), \
                 patch.object(network.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="HTTP 404")):
                with patch.object(network.sys, "argv", ["network.py", "install"]):
                    network.main()
                with patch.object(network.sys, "argv", ["network.py", "verify"]):
                    network.main()
                self.assertTrue(json.loads(output_path.read_text())["ok"])
        self.assertFalse(any("create" in call for call in calls))

    def test_locked_fixture_and_join(self):
        database = module("order_database", "db/database.py")
        rows, digest = database.fixture()
        self.assertEqual(len(digest), 64)
        prices = {r['product_id']: int(r['unit_price']) for r in rows['products.csv']}
        self.assertEqual(len(prices), 3)
        self.assertEqual(len(rows['orders.csv']), 4)
        self.assertEqual(sum(int(r['quantity']) * prices[r['product_id']] for r in rows['orders.csv']), 750)

    def test_fixture_digest_mismatch_is_rejected(self):
        database = module("order_database_bad", "db/database.py")
        original = Path.read_bytes
        def changed(path):
            return b"tampered" if path.name == "orders.csv" else original(path)
        with patch.object(Path, "read_bytes", changed):
            with self.assertRaisesRegex(ValueError, "data digest"):
                database.fixture()

    def test_ownership_checks_and_missing_results_fail(self):
        network = module("order_network", "platform/network.py")
        with self.assertRaises(ValueError):
            network.require(False, "ownership conflict")
        with self.assertRaises(ValueError):
            network.entries({})
        self.assertEqual(network.entries({"datas": [{"order_id": "O001"}]}), [{"order_id": "O001"}])

    def test_network_references_match_fixture(self):
        network = json.loads((ROOT / "kn/order_basics.json").read_text())
        self.assertEqual(network["branch"], "main")
        self.assertEqual({o['id'] for o in network['object_types']}, {'products', 'orders'})
        relation = network['relation_types'][0]
        self.assertEqual(relation['source_object_type_id'], 'orders')
        self.assertEqual(relation['target_object_type_id'], 'products')
