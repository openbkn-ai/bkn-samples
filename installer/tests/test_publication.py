import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.publication.validate import compare_baseline, validate_catalog


ROOT = Path(__file__).resolve().parents[2]


class PublicationTest(unittest.TestCase):
    def test_bootstrap_catalog_is_valid_and_contains_no_unverified_release(self):
        catalog, _ = validate_catalog(ROOT, official=True)
        catalog["spec"]["entries"] = []
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "catalog.json").write_text(json.dumps(catalog))
            _, entries = validate_catalog(root, official=True)
            self.assertEqual(entries, {})

    def test_draft_examples_still_validate(self):
        validate_catalog(ROOT / "protocol/draft/examples")

    def test_changed_catalog_requires_increasing_sequence(self):
        baseline = validate_catalog(ROOT, official=True)
        catalog = copy.deepcopy(baseline[0])
        catalog["metadata"]["revision"] = "changed"
        with self.assertRaisesRegex(ValueError, "sequence"):
            compare_baseline((catalog, {}), baseline)
        catalog["metadata"]["sequence"] += 1
        compare_baseline((catalog, {}), baseline)


if __name__ == "__main__":
    unittest.main()
