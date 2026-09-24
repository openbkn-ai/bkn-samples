import json
import tempfile
import unittest
from pathlib import Path

import yaml

from installer.contract import (
    OFFICIAL_SOURCE_REPO,
    ContractError,
    build_manifest_index,
    check_manifest_index,
    validate_repository,
)

ROOT = Path(__file__).resolve().parents[2]
REVISION = "a" * 40


def write_sample(root: Path, folder: str, document: dict, hooks: bool = True) -> None:
    sample = root / "samples" / folder
    sample.mkdir(parents=True)
    (sample / "sample.yaml").write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    if document["spec"]["data"]["mode"] == "embedded":
        (sample / "data").mkdir()
    if hooks:
        for relative in document["spec"]["hooks"].values():
            path = sample / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def base_document(name: str = "fixture", engine: str = "mariadb", hook: str = "db/init.sh") -> dict:
    return {
        "apiVersion": "samples.openbkn.ai/v1alpha1",
        "kind": "Sample",
        "metadata": {"name": name, "displayName": "Fixture", "summary": "A fixture sample."},
        "spec": {
            "studio": {"licenseNote": "fixture", "questions": []},
            "database": {"engine": engine, "name": f"{name.replace('-', '_')}_db", "expectedTables": 1},
            "data": {"mode": "embedded"},
            "knowledgeNetwork": {"id": f"{name}_kn", "displayName": "Fixture network"},
            "capabilities": {"required": False},
            "hooks": {
                "dbInit": hook,
                "dbVerify": "db/verify.sh",
                "platformInstall": "platform/install.sh",
                "platformVerify": "platform/verify.sh",
            },
        },
    }


class SupplyContractTest(unittest.TestCase):
    def test_repository_accepts_supply_chain(self):
        samples = validate_repository(ROOT)
        names = [sample["metadata"]["name"] for sample in samples]
        self.assertEqual(names, ["supply-chain", "world-cup"])

    def test_index_uses_version_and_official_repo(self):
        index = build_manifest_index(ROOT, REVISION)
        self.assertEqual(index["version"], (ROOT / "VERSION").read_text(encoding="utf-8").strip())
        self.assertEqual(index["sourceRepo"], OFFICIAL_SOURCE_REPO)
        self.assertEqual(index["samples"][0]["name"], "supply-chain")
        self.assertEqual(index["samples"][0]["expectedTables"], 12)
        check_manifest_index(ROOT, index)

    def test_rejects_other_source_repo(self):
        with self.assertRaises(ContractError):
            build_manifest_index(ROOT, REVISION, source_repo="https://github.com/example/samples")

    def test_rejects_version_mismatch(self):
        index = build_manifest_index(ROOT, REVISION)
        index["version"] = "9.9.9"
        with self.assertRaises(ContractError) as caught:
            check_manifest_index(ROOT, index)
        self.assertIn("does not match VERSION", str(caught.exception))


class FixtureContractTest(unittest.TestCase):
    def make_repo(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        (root / "samples").mkdir()
        return root

    def test_rejects_postgres_engine(self):
        root = self.make_repo()
        write_sample(root, "bad-engine", base_document(engine="postgres"))
        with self.assertRaises(ContractError) as caught:
            validate_repository(root)
        self.assertIn("mariadb", str(caught.exception))

    def test_rejects_parent_hook_path(self):
        root = self.make_repo()
        write_sample(root, "bad-path", base_document(hook="../db/init.sh"), hooks=False)
        with self.assertRaises(ContractError) as caught:
            validate_repository(root)
        self.assertIn("stay inside", str(caught.exception))

    def test_rejects_duplicate_alias(self):
        root = self.make_repo()
        first = base_document("alpha")
        second = base_document("beta")
        second["metadata"]["aliases"] = ["alpha"]
        write_sample(root, "alpha", first)
        write_sample(root, "beta", second)
        with self.assertRaises(ContractError) as caught:
            validate_repository(root)
        self.assertIn("alpha", str(caught.exception))

    def test_index_round_trip(self):
        root = self.make_repo()
        write_sample(root, "alpha", base_document("alpha"))
        index = build_manifest_index(root, REVISION)
        check_manifest_index(root, index)
        encoded = json.dumps(index)
        check_manifest_index(root, json.loads(encoded))


if __name__ == "__main__":
    unittest.main()
