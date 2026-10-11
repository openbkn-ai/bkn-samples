"""Creation receipts never adopt pre-existing execution resources."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class OwnershipReceiptTest(unittest.TestCase):
    def test_created_ids_are_recorded_and_other_ids_are_rejected(self):
        root = Path(__file__).resolve().parents[2]
        for path in (root / "samples/supply_ontology_hand/tools/ownership_receipt.py",
                     root / "samples/world-cup/platform/ownership_receipt.py"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                spec = importlib.util.spec_from_file_location("receipt", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                with patch.dict(os.environ, {"BKN_SAMPLE_RECEIPT": str(Path(directory) / "owned.json")}):
                    with self.assertRaises(RuntimeError):
                        module.require_owned("toolboxes", "pre-existing")
                    module.remember("toolboxes", "created")
                    module.remember("toolboxes", "created")
                    module.require_owned("toolboxes", "created")
                    self.assertEqual(module.read()["toolboxes"], ["created"])
                    self.assertEqual(module.read()["skills"], [])
                    with self.assertRaises(RuntimeError):
                        module.require_owned("skills", "unrelated")
