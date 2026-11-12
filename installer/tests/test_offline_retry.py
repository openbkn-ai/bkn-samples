import io
import json
import tempfile
from contextlib import redirect_stderr
import unittest
from unittest.mock import patch
from pathlib import Path

from installer.deploy_database import DeployError
from installer.offline_bundle import OfflinePackages
from installer.remote_installation import RemoteInstallation
from installer.runtime import install_sample
from installer.studio_api import ApiError, _read_state, _write_failed

ROOT = Path(__file__).resolve().parents[2]


class OfflineRetryTest(unittest.TestCase):
    def test_failed_offline_install_must_be_cleaned_before_package_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            runtime = RemoteInstallation(ROOT, state, "0.2.0", "arm64", [],
                                         "ghcr.io/openbkn-ai/executor@sha256:" + "a" * 64)
            offline = OfflinePackages(ROOT, state, runtime)
            destination = offline.directory / "supply-chain"
            destination.mkdir(parents=True)
            (destination / "package.tar.gz").write_bytes(b"package")
            (state / "supply-chain.json").write_text(json.dumps({
                "status": "failed", "offlineRelease": {"packageDigest": "old"}}))

            with self.assertRaises(ApiError) as caught:
                offline.delete_package("supply-chain", "admin")
            self.assertEqual(caught.exception.code, "offline_in_use")
            self.assertTrue(destination.exists())
            self.assertTrue((state / "supply-chain.json").exists())
            cleaned = {"status": "uninstalled", "offlineRelease": {"packageDigest": "old"}}
            (state / "supply-chain.json").write_text(json.dumps(cleaned))
            self.assertEqual(offline.delete_package("supply-chain", "admin"),
                             {"sample": "supply-chain", "deleted": True})
            self.assertEqual(_read_state(state, "supply-chain"), cleaned)

    def test_withdrawing_offline_package_keeps_remote_failure_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            runtime = RemoteInstallation(ROOT, state, "0.2.0", "arm64", [],
                                         "ghcr.io/openbkn-ai/executor@sha256:" + "a" * 64)
            offline = OfflinePackages(ROOT, state, runtime)
            destination = offline.directory / "supply-chain"
            destination.mkdir(parents=True)
            (destination / "package.tar.gz").write_bytes(b"package")
            remote_failure = {"status": "failed", "remoteRelease": {"version": "0.1.0"}}
            state_path = state / "supply-chain.json"
            state_path.write_text(json.dumps(remote_failure))

            offline.delete_package("supply-chain", "admin")

            self.assertEqual(json.loads(state_path.read_text()), remote_failure)

    def test_database_failure_preserves_offline_identity_for_retry(self):
        for code in ("image_unavailable", "storage_class_missing", "database_not_ready"):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                state = Path(directory)
                runtime = RemoteInstallation(ROOT, state, "0.2.0", "arm64", [],
                                             "ghcr.io/openbkn-ai/executor@sha256:" + "a" * 64)
                offline = OfflinePackages(ROOT, state, runtime)
                release = {"sample": "supply-chain", "version": "0.1.0",
                           "packageDigest": "sha256:" + "b" * 64,
                           "manifestSha256": "c" * 64,
                           "dataImageRef": "ghcr.io/openbkn-ai/data@sha256:" + "d" * 64,
                           "releaseNotes": {"version": "0.1.0", "documents": []}}
                cached = offline.directory / "supply-chain"
                cached.mkdir(parents=True)
                (cached / "release.json").write_text(json.dumps(release))
                offline.prepare(release)
                original = _read_state(state, "supply-chain")

                def deploy(_sample):
                    raise DeployError(code, "database deployment failed")

                with patch("installer.runtime.shared_database.configured", return_value=True), \
                     patch("installer.runtime.shared_database.prepare", side_effect=DeployError(code, "database operation failed")), \
                     self.assertRaises(ApiError):
                    install_sample(sample="supply-chain", actor_role="admin", state_dir=state,
                                   root=ROOT, version="0.1.0", deploy=deploy,
                                   kubectl=None, run=None)
                failed = _read_state(state, "supply-chain")
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["stages"], {"database": "failed"})
                for key in ("offlineRelease", "packageDigest", "manifestSha256",
                            "dataImageRef", "releaseNotesSnapshot"):
                    self.assertEqual(failed[key], original[key])
                offline.prepare(release, retry=True)
                self.assertEqual(_read_state(state, "supply-chain")["status"], "installing")

    def _failed_offline(self, state, executor_image="ghcr.io/openbkn-ai/executor@sha256:" + "a" * 64):
        runtime = RemoteInstallation(ROOT, state, "0.2.0", "arm64", [], executor_image)
        offline = OfflinePackages(ROOT, state, runtime)
        release = {"sample": "supply-chain", "version": "0.1.0", "packageDigest": "sha256:" + "b" * 64,
                   "manifestSha256": "c" * 64, "dataImageRef": None,
                   "releaseNotes": {"version": "0.1.0", "documents": []}}
        cached = offline.directory / "supply-chain"
        cached.mkdir(parents=True)
        (cached / "release.json").write_text(json.dumps(release))
        offline.prepare(release)
        failed = _read_state(state, "supply-chain")
        failed.update(status="failed", error={"code": "install_failed", "message": "proxy sync pending"})
        (state / "supply-chain.json").write_text(json.dumps(failed))
        return offline, release, failed

    def test_retry_after_a_service_upgrade_uses_the_current_executor_for_the_same_package(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            offline, release, failed = self._failed_offline(state)
            failed["offlineRelease"].update(executorDigest="sha256:" + "0" * 64,
                                            executorImage="ghcr.io/openbkn-ai/executor:old")
            (state / "supply-chain.json").write_text(json.dumps(failed))
            output = io.StringIO()
            with redirect_stderr(output):
                offline.prepare(release, retry=True)
            retried = _read_state(state, "supply-chain")
            self.assertEqual(retried["status"], "installing")
            self.assertNotIn("error", retried)
            self.assertEqual(retried["id"], failed["id"])
            self.assertEqual(retried["offlineRelease"]["packageDigest"], release["packageDigest"])
            self.assertEqual(retried["offlineRelease"]["executorImage"], offline.runtime.executor_image)
            self.assertEqual(retried["offlineRelease"]["executorDigest"], offline.runtime.executor_digest)
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual([e["step"] for e in events], ["retry-executor-changed"])
            self.assertEqual(events[0]["previous_executor_image"], "ghcr.io/openbkn-ai/executor:old")

    def test_retry_refusals_are_conflicts_and_leave_the_record_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            offline, release, failed = self._failed_offline(state)
            other = {**failed, "offlineRelease": {**failed["offlineRelease"], "packageDigest": "sha256:" + "f" * 64}}
            installed = {**failed, "status": "installed"}
            for record, code in ((other, "version_changed"), (installed, "already_installing")):
                with self.subTest(code=code):
                    (state / "supply-chain.json").write_text(json.dumps(record))
                    with self.assertRaises(ApiError) as caught:
                        offline.prepare(release, retry=True)
                    self.assertEqual((caught.exception.status, caught.exception.code), (409, code))
                    self.assertEqual(_read_state(state, "supply-chain"), record)

    def test_missing_executor_image_is_a_conflict_not_a_server_error(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            offline, release, failed = self._failed_offline(state)
            offline.runtime.executor_image = ""
            with self.assertRaises(ApiError) as caught:
                offline.prepare(release, retry=True)
            self.assertEqual((caught.exception.status, caught.exception.code), (409, "runtime_upgrade_required"))
            self.assertEqual(_read_state(state, "supply-chain"), failed)

    def test_failure_does_not_copy_artifact_identity_from_another_version(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "supply-chain.json").write_text(json.dumps({
                "version": "0.1.0", "offlineRelease": {"packageDigest": "old"},
                "packageDigest": "old"}))
            _write_failed(state, "supply-chain", "0.2.0", "image_unavailable", "failed")
            failed = _read_state(state, "supply-chain")
            self.assertNotIn("offlineRelease", failed)
            self.assertNotIn("packageDigest", failed)

    def test_retry_failure_preserves_resource_receipts_for_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            original = {"sample": "supply-chain", "id": "inst-old", "version": "0.1.4", "status": "installing",
                        "catalogId": "catalog-owned", "resources": {"knowledgeNetworkId": "network-owned",
                        "ownedExecution": {"skills": ["skill-owned"], "toolboxes": []}}}
            (state / "supply-chain.json").write_text(json.dumps(original))
            _write_failed(state, "supply-chain", "0.1.4", "database_not_ready", "database retry failed")
            failed = _read_state(state, "supply-chain")
            self.assertEqual(failed["catalogId"], original["catalogId"])
            self.assertEqual(failed["resources"], original["resources"])
            _write_failed(state, "supply-chain", "0.1.5", "database_not_ready", "different release")
            changed = _read_state(state, "supply-chain")
            self.assertNotIn("catalogId", changed)
            self.assertNotIn("resources", changed)
