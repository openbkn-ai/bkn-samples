import copy
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from installer.remote_bundle import (AssetRedirect, compatibility, extract_package,
                                     load_release, sha, validate_package)
from installer.remote_installation import RemoteInstallation
from installer.remote_catalog import merge_remote
from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, _write_failed
from installer.task_runner import InstallationRunner

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "protocol/draft/examples"


class RemoteBundleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.entry = json.loads((EXAMPLES / "catalog.json").read_text())["spec"]["entries"][0]
        self.sample = json.loads((EXAMPLES / "supply-chain/releases/1.0.0/sample.json").read_text())
        self.sample["spec"]["contents"]["knowledgeNetworks"][0]["directory"] = "kn"
        self.package = self.sample["spec"]["artifacts"][0]
        self.package["locations"] = ["https://github.com/openbkn-ai/bkn-samples/releases/download/sample-supply-chain-v1.0.0/package.tar.gz"]
        self.sample["spec"]["artifacts"][1]["locations"] = ["oci://ghcr.io/openbkn-ai/bkn-samples"]
        note = self.sample["spec"]["release"]["releaseNotes"][0]
        self.note = b"# Fixed release\n"
        note["digest"] = sha(self.note)
        self.entry["releaseNotes"]["documents"][0]["digest"] = sha(self.note)
        self.archive = self.root / "package.tar.gz"
        files = {"sample.yaml": (ROOT / "samples/supply_ontology_hand/sample.yaml").read_bytes(),
                 "data/data.txt": b"reviewed test data", "functions/README": b"functions", "skills/README": b"skills",
                 "kn/supply_ontology_hand.json": json.dumps({"id": "supply_ontology_hand",
                     "object_types": [{"id": "supply_ontology_hand_inventory"}]}).encode(),
                 "releases/1.0.0/release-notes.zh-CN.md": self.note}
        for name in ("db/init.sh", "db/verify.sh", "platform/install.sh", "platform/verify.sh"):
            files[name] = b"#!/bin/sh\nexit 0\n"
        with tarfile.open(self.archive, "w:gz") as archive:
            for name, data in files.items():
                member = tarfile.TarInfo(name)
                member.size, member.mode = len(data), 0o755 if name.endswith(".sh") else 0o644
                archive.addfile(member, io.BytesIO(data))
        self.package["digest"] = sha(self.archive.read_bytes())
        self.proof = {"sampleId": "supply-chain", "version": "1.0.0", "freshInstallation": True,
                      "packageDigest": self.package["digest"],
                      "dataImageRef": "ghcr.io/openbkn-ai/bkn-samples@" + self.sample["spec"]["artifacts"][1]["digest"],
                      "checks": [{"name": name, "passed": True} for name in ("database", "knowledge", "capabilities", "scenario")]}
        prefix = "https://raw.githubusercontent.com/openbkn-ai/bkn-samples/" + "a" * 40 + "/samples/supply_ontology_hand/releases/1.0.0/"
        self.entry["manifest"]["url"] = prefix + "sample.json"
        self.entry["verification"]["url"] = prefix + "verification.json"
        self.entry["releaseNotes"]["documents"][0]["url"] = prefix + "release-notes.zh-CN.md"

    def load(self):
        manifest, proof = json.dumps(self.sample).encode(), json.dumps(self.proof).encode()
        self.entry["manifest"]["digest"] = sha(manifest)
        self.entry["verification"]["digest"] = sha(proof)
        documents = {self.entry["manifest"]["url"]: manifest,
                     self.entry["verification"]["url"]: proof,
                     self.entry["releaseNotes"]["documents"][0]["url"]: self.note}
        def reader(url, limit):
            data = documents[url]
            self.assertLessEqual(len(data), limit)
            return data
        self.reader = reader
        return load_release(self.entry, ROOT / "protocol/draft/schemas/sample.schema.json", "0.2.0", "arm64",
                            self.entry["requires"]["capabilities"], reader)

    def test_fixed_release_extracts_and_matches_existing_runtime_contract(self):
        release = self.load()
        target = self.root / "samples/supply-chain"
        extract_package(self.archive, target, release["package"])
        document = validate_package(target, release)
        self.assertEqual(document["metadata"]["name"], "supply-chain")
        self.assertTrue((target / "db/init.sh").stat().st_mode & 0o100)
        self.assertEqual(release["releaseNotes"]["documents"][0]["content"], self.note.decode())

    def test_rejects_a_rewritten_cached_archive_before_extracting(self):
        release = self.load()
        self.archive.write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "digest"):
            extract_package(self.archive, self.root / "sample", release["package"])
        self.assertFalse((self.root / "sample").exists())

    def test_rejects_archive_links_traversal_duplicates_and_special_files(self):
        for kind in ("link", "traversal", "duplicate", "device"):
            with self.subTest(kind=kind):
                path = self.root / (kind + ".tar.gz")
                with tarfile.open(path, "w:gz") as archive:
                    member = tarfile.TarInfo("../escape" if kind == "traversal" else "file")
                    if kind == "link":
                        member.type, member.linkname = tarfile.SYMTYPE, "outside"
                    if kind == "device":
                        member.type = tarfile.CHRTYPE
                    archive.addfile(member)
                    if kind == "duplicate":
                        archive.addfile(member)
                with self.assertRaises(ValueError):
                    extract_package(path, self.root / kind, {"digest": sha(path.read_bytes())})

    def test_receipt_must_bind_the_same_package_and_pass_all_checks(self):
        for change in ("digest", "fresh", "failed"):
            with self.subTest(change=change):
                original = copy.deepcopy(self.proof)
                if change == "digest":
                    self.proof["packageDigest"] = "sha256:" + "b" * 64
                elif change == "fresh":
                    self.proof["freshInstallation"] = False
                else:
                    self.proof["checks"][0]["passed"] = False
                with self.assertRaises(ValueError):
                    self.load()
                self.proof = original

    def test_external_artifacts_and_catalog_mismatch_are_rejected(self):
        self.package["locations"] = ["https://example.com/package.tar.gz"]
        with self.assertRaisesRegex(ValueError, "official"):
            self.load()
        self.package["locations"] = ["https://github.com/openbkn-ai/bkn-samples/releases/download/sample-supply-chain-v1.0.0/package.tar.gz"]
        self.sample["metadata"]["version"] = "1.1.0"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.load()

    def test_native_binding_and_packaged_notes_are_checked(self):
        release = self.load()
        target = self.root / "sample"
        extract_package(self.archive, target, release["package"])
        release["manifest"]["spec"]["delivery"]["bindings"][0]["objectTypeId"] = "missing"
        with self.assertRaisesRegex(ValueError, "binding"):
            validate_package(target, release)
        release["manifest"]["spec"]["delivery"]["bindings"][0]["objectTypeId"] = "supply_ontology_hand_inventory"
        (target / "releases/1.0.0/release-notes.zh-CN.md").write_text("changed")
        with self.assertRaisesRegex(ValueError, "notes"):
            validate_package(target, release)

    def test_compatibility_requires_explicit_platform_and_capabilities(self):
        required = self.entry["requires"]
        for version, architecture, capabilities in (("", "arm64", required["capabilities"]),
                ("0.2.1", "arm64", required["capabilities"]), ("0.2.0", "riscv64", required["capabilities"]),
                ("0.2.0", "arm64", [])):
            with self.subTest(version=version, architecture=architecture, capabilities=capabilities):
                with self.assertRaises(ValueError):
                    compatibility(required, version, architecture, capabilities)

    def test_asset_redirect_cannot_target_local_or_third_party_hosts(self):
        for url in ("http://localhost/file", "https://example.com/file", "https://github.com/other/file"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                AssetRedirect().redirect_request(None, None, 302, "Found", {}, url)

    def coordinator(self):
        return RemoteInstallation(ROOT, self.root / "state", "0.2.0", "arm64", self.entry["requires"]["capabilities"],
                                  "ghcr.io/openbkn-ai/bkn-sample-studio@sha256:" + "d" * 64)

    def test_remote_plan_is_saved_before_work_and_worker_uses_fixed_files(self):
        self.load()
        coordinator = self.coordinator()
        coordinator.prepare(self.entry)
        saved = _read_state(coordinator.state_dir, "supply-chain")
        self.assertEqual(saved["remoteRelease"]["entry"], self.entry)
        self.entry["version"] = "1.1.0"
        def downloader(package, target):
            target.write_bytes(self.archive.read_bytes())
        roots = []
        def install(root, version, image, retry):
            roots.append(root)
            self.assertEqual(version, "1.0.0")
            self.assertEqual((root / "VERSION").read_text(), "1.0.0")
            self.assertTrue((root / "samples/supply-chain/platform/install.sh").exists())
            self.assertFalse(retry)
            return {"ok": True}
        self.assertEqual(coordinator.execute("supply-chain", install, reader=self.reader, downloader=downloader), {"ok": True})
        self.assertFalse(roots[0].exists())
        self.assertEqual(_read_state(coordinator.state_dir, "supply-chain")["version"], "1.0.0")

    def test_failed_remote_plan_survives_restart_and_ignores_new_catalog_version(self):
        self.load()
        coordinator = self.coordinator()
        coordinator.prepare(self.entry)
        runner = InstallationRunner(coordinator.state_dir, [])
        runner.recover_interrupted()
        failed = _read_state(coordinator.state_dir, "supply-chain")
        self.assertEqual(failed["error"]["code"], "install_interrupted")
        self.assertIn("supply-chain", runner.locks)
        self.entry["version"] = "1.1.0"
        coordinator.prepare_retry("supply-chain", failed["id"])
        retried = _read_state(coordinator.state_dir, "supply-chain")
        self.assertEqual(retried["remoteRelease"]["entry"]["version"], "1.0.0")
        _write_failed(coordinator.state_dir, "supply-chain", "1.0.0", "image_unavailable", "unavailable")
        self.assertEqual(_read_state(coordinator.state_dir, "supply-chain")["remoteRelease"], failed["remoteRelease"])

    def test_retry_refuses_a_changed_executor_without_replacing_the_record(self):
        self.load()
        coordinator = self.coordinator()
        coordinator.prepare(self.entry)
        failed = _read_state(coordinator.state_dir, "supply-chain")
        failed["status"] = "failed"
        write_json(coordinator.state_dir / "supply-chain.json", failed)
        coordinator.executor_digest = "changed"
        with self.assertRaises(ApiError) as error:
            coordinator.prepare_retry("supply-chain", failed["id"])
        self.assertEqual(error.exception.code, "version_changed")
        self.assertEqual(_read_state(coordinator.state_dir, "supply-chain"), failed)

    def test_catalog_preserves_remote_installed_state_without_a_source_cache(self):
        self.load()
        coordinator = self.coordinator()
        coordinator.prepare(self.entry)
        installed = _read_state(coordinator.state_dir, "supply-chain")
        installed.update({"status": "installed", "installedAt": "2026-10-09T08:00:00Z",
                          "resources": {"knowledgeNetworkId": "supply_ontology_hand"}})
        write_json(coordinator.state_dir / "supply-chain.json", installed)
        result = merge_remote({"samples": []}, [], coordinator.state_dir, "admin", coordinator)
        self.assertEqual(result["samples"][0]["status"], "installed")
        self.assertEqual(result["samples"][0]["installedVersion"], "1.0.0")
        self.assertFalse(result["samples"][0]["installable"])
        self.assertEqual(result["samples"][0]["knowledgeNetwork"]["id"], "supply_ontology_hand")


if __name__ == "__main__":
    unittest.main()
