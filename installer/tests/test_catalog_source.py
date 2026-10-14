import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.catalog_source import OfficialCatalog


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "protocol/draft/schemas/catalog.schema.json"
PINNED = "https://raw.githubusercontent.com/openbkn-ai/bkn-samples/" + "a" * 40 + "/catalog.json"


class PinnedCatalogTests(unittest.TestCase):
    def test_accepts_official_commit_catalog_without_reading_branch_ref(self):
        catalog = (ROOT / "catalog.json").read_bytes()
        with tempfile.TemporaryDirectory() as directory, patch(
            "installer.catalog_source.read_url", return_value=catalog
        ) as read:
            source = OfficialCatalog(Path(directory), SCHEMA, PINNED)
            result = source.refresh()
        self.assertEqual(result["status"], "updated")
        read.assert_called_once_with(PINNED, 2 * 1024 * 1024)

    def test_rejects_non_catalog_pinned_path(self):
        with self.assertRaises(ValueError):
            OfficialCatalog(Path(tempfile.mkdtemp()), SCHEMA, PINNED.replace("catalog.json", "README.md"))


class BundledCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state = Path(self.temporary.name)
        self.catalog = json.loads((ROOT / "catalog.json").read_text())

    def cached(self, sequence):
        catalog = json.loads(json.dumps(self.catalog))
        catalog["metadata"]["sequence"] = sequence
        catalog["metadata"]["revision"] = f"catalog-{sequence:06d}"
        cache = {"catalog": catalog, "commit": "a" * 40, "fetchedAt": "2026-10-13T15:45:03Z"}
        path = self.state / "catalogs" / "official.json"
        path.parent.mkdir()
        path.write_text(json.dumps(cache))
        return cache

    def source(self):
        return OfficialCatalog(self.state, SCHEMA, bundled_catalog=ROOT / "catalog.json")

    def test_first_start_reads_bundled_directory_without_network(self):
        with patch("installer.catalog_source.read_url") as network:
            source = self.source()
        self.assertEqual(source.entries(), self.catalog["spec"]["entries"])
        network.assert_not_called()
        self.assertIsNone(source.metadata()["lastSuccessfulRefreshAt"])
        self.assertEqual(source.metadata()["status"], "not_refreshed")

    def test_explicit_catalog_pin_keeps_its_existing_behavior(self):
        source = OfficialCatalog(self.state, SCHEMA, PINNED, bundled_catalog=ROOT / "catalog.json")
        self.assertEqual(source.entries(), [])
        with patch("installer.catalog_source.read_url", return_value=json.dumps(self.catalog).encode()) as network:
            self.assertEqual(source.refresh()["status"], "updated")
        network.assert_called_once_with(PINNED, 2 * 1024 * 1024)

    def test_image_update_supersedes_an_older_cached_directory(self):
        old = self.cached(self.catalog["metadata"]["sequence"] - 1)
        source = self.source()
        self.assertEqual(source.cache["catalog"], self.catalog)
        self.assertIsNone(source.metadata()["lastSuccessfulRefreshAt"])
        self.assertEqual(json.loads(source.path.read_text()), old)

    def test_newer_remote_cache_is_not_downgraded_by_the_image(self):
        newer = self.cached(self.catalog["metadata"]["sequence"] + 1)
        self.assertEqual(self.source().cache, newer)

    def test_equal_sequence_preserves_successful_refresh_metadata(self):
        cached = self.cached(self.catalog["metadata"]["sequence"])
        self.assertEqual(self.source().cache, cached)

    def test_network_failure_keeps_the_bundled_directory(self):
        source = self.source()
        with patch("installer.catalog_source.read_url", side_effect=OSError("unreachable")):
            self.assertEqual(source.refresh()["status"], "failed")
        self.assertEqual(source.entries(), self.catalog["spec"]["entries"])

    def test_invalid_disk_cache_falls_back_to_bundled_directory(self):
        path = self.state / "catalogs" / "official.json"
        path.parent.mkdir()
        path.write_text("invalid json")
        source = self.source()
        self.assertEqual(source.entries(), self.catalog["spec"]["entries"])
        self.assertEqual(source.metadata()["status"], "not_refreshed")


if __name__ == "__main__":
    unittest.main()
