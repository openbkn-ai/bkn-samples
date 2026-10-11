import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.publication.validate import compare_baseline, validate_catalog, validate_verification


ROOT = Path(__file__).resolve().parents[2]


class PublicationTest(unittest.TestCase):
    def test_publication_requires_same_receipt_checks_as_installer(self):
        sample = json.loads((ROOT / "samples/order-basics/releases/0.1.0/sample.json").read_text())
        proof = json.loads((ROOT / "samples/order-basics/releases/0.1.0/verification.json").read_text())
        entry = {"sampleId": "order-basics", "version": "0.1.0"}
        with self.assertRaisesRegex(ValueError, "verification checks"):
            validate_verification(proof, entry, sample)
        proof["checks"].append({"name": "capabilities", "passed": True})
        validate_verification(proof, entry, sample)
        proof["packageDigest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "other artifacts"):
            validate_verification(proof, entry, sample)
        sample["spec"]["artifacts"] = []
        with self.assertRaisesRegex(ValueError, "archive and data image"):
            validate_verification(proof, entry, sample)

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
        entries = {(entry["sampleId"], entry["version"]): entry for entry in baseline[0]["spec"]["entries"]}
        with self.assertRaisesRegex(ValueError, "sequence"):
            compare_baseline((catalog, entries), baseline)
        catalog["metadata"]["sequence"] += 1
        compare_baseline((catalog, entries), baseline)


if __name__ == "__main__":
    unittest.main()
