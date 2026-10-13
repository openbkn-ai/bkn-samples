import tempfile
import unittest
from pathlib import Path

from installer.tests.test_contract import base_document, write_sample
from tools.publication.plan_data_image import plan


class DataImagePlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write_sample(self.root, "different_folder", base_document("new-demo"))
        sample = self.root / "samples/different_folder"
        (sample / "db/Dockerfile").write_text("FROM scratch\n")
        notes = sample / "releases/1.2.3"
        notes.mkdir(parents=True)
        (notes / "release-notes.en-US.md").write_text("Release\n")

    def test_new_identity_resolves_directory_without_allowlist(self):
        result = plan(self.root, "new-demo", "1.2.3", "repository")
        self.assertEqual(result["context"], ".")
        self.assertEqual(result["dockerfile"], "samples/different_folder/db/Dockerfile")
        self.assertEqual(plan(self.root, "new-demo", "1.2.3", "sample")["context"], "samples/different_folder")

    def test_unknown_identity_version_and_injection_are_rejected(self):
        for name, version in [("unknown", "1.2.3"), ("../new-demo", "1.2.3"),
                              ("new-demo\ncontext=/", "1.2.3"), ("new-demo", "1.2.4"),
                              ("new-demo", "1.2.3\n")]:
            with self.assertRaises(ValueError):
                plan(self.root, name, version, "repository")

    def test_symlink_dockerfile_is_rejected(self):
        dockerfile = self.root / "samples/different_folder/db/Dockerfile"
        dockerfile.unlink()
        dockerfile.symlink_to(self.root / "samples/different_folder/releases/1.2.3/release-notes.en-US.md")
        with self.assertRaises(ValueError):
            plan(self.root, "new-demo", "1.2.3", "repository")
