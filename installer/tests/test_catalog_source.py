import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from catalog_source import OfficialCatalog


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "protocol/draft/schemas/catalog.schema.json"
PINNED = "https://raw.githubusercontent.com/openbkn-ai/bkn-samples/" + "a" * 40 + "/catalog.json"


class PinnedCatalogTests(unittest.TestCase):
    def test_accepts_official_commit_catalog_without_reading_branch_ref(self):
        catalog = (ROOT / "catalog.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory, patch(
            "catalog_source.read_url", return_value=catalog
        ) as read:
            source = OfficialCatalog(Path(directory), SCHEMA, PINNED)
            result = source.refresh()
        self.assertEqual(result["status"], "updated")
        read.assert_called_once_with(PINNED, 2 * 1024 * 1024)

    def test_rejects_non_catalog_pinned_path(self):
        with self.assertRaises(ValueError):
            OfficialCatalog(Path(tempfile.mkdtemp()), SCHEMA, PINNED.replace("catalog.json", "README.md"))


if __name__ == "__main__":
    unittest.main()
