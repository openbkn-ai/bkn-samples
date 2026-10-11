import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / "samples/order-basics"


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class OrderBasicsTest(unittest.TestCase):
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
        self.assertEqual({o['id'] for o in network['object_types']}, {'products', 'orders'})
        relation = network['relation_types'][0]
        self.assertEqual(relation['source_object_type_id'], 'orders')
        self.assertEqual(relation['target_object_type_id'], 'products')
