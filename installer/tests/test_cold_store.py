import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from installer.ci.verify_cold_store import verify


class ColdStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.blobs = {}
        self.layer = self.add_blob(b"compressed layer fixture")
        config = self.add_blob(json.dumps({"architecture": "arm64", "os": "linux"}).encode())
        manifest = self.add_blob(json.dumps({"config": {"digest": config}, "layers": [
            {"digest": self.layer, "size": len(self.blobs[self.layer])}
        ]}).encode())
        self.index = self.add_blob(json.dumps({"manifests": [
            {"digest": manifest, "platform": {"os": "linux", "architecture": "arm64"}}
        ]}).encode())
        self.write_hashes()

    def add_blob(self, value):
        digest = "sha256:" + hashlib.sha256(value).hexdigest()
        self.blobs[digest] = value
        return digest

    def write_hashes(self):
        (self.directory / "blob-hashes.txt").write_text("".join(
            f"{digest[7:]}  /store/blobs/sha256/{digest[7:]}\n" for digest in self.blobs
        ))

    def read(self, command):
        digest = "sha256:" + Path(command[-1]).name
        if "stat" in command:
            return str(len(self.blobs[digest])).encode()
        return self.blobs[digest]

    def test_verifies_native_metadata_and_every_compressed_layer(self):
        with patch("subprocess.check_output", side_effect=self.read):
            verify("harness", self.directory, self.index, "arm64")
        result = json.loads((self.directory / "verification.json").read_text())
        self.assertTrue(result["passed"])
        self.assertEqual(result["layers"][0]["digest"], self.layer)

    def test_missing_layer_is_not_success(self):
        del self.blobs[self.layer]
        self.write_hashes()
        with patch("subprocess.check_output", side_effect=self.read), self.assertRaisesRegex(ValueError, "missing"):
            verify("harness", self.directory, self.index, "arm64")
        self.assertFalse((self.directory / "verification.json").exists())

    def test_content_address_mismatch_fails(self):
        path = self.directory / "blob-hashes.txt"
        path.write_text(path.read_text().replace(self.layer[7:], "0" * 64, 1))
        with self.assertRaisesRegex(ValueError, "hash"):
            verify("harness", self.directory, self.index, "arm64")

    def test_wrong_native_architecture_fails(self):
        with patch("subprocess.check_output", side_effect=self.read), self.assertRaisesRegex(ValueError, "native"):
            verify("harness", self.directory, self.index, "amd64")

    def test_changed_metadata_fails(self):
        self.blobs[self.index] = b"{}"
        with patch("subprocess.check_output", side_effect=self.read), self.assertRaisesRegex(ValueError, "digest"):
            verify("harness", self.directory, self.index, "arm64")

    def test_wrong_layer_size_fails(self):
        def wrong_size(command):
            return b"1" if "stat" in command else self.read(command)
        with patch("subprocess.check_output", side_effect=wrong_size), self.assertRaisesRegex(ValueError, "size"):
            verify("harness", self.directory, self.index, "arm64")
