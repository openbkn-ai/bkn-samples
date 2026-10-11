import json
import tempfile
import unittest
from pathlib import Path

from installer.deploy_database import DeployError
from installer.offline_bundle import OfflinePackages
from installer.remote_installation import RemoteInstallation
from installer.runtime import install_sample
from installer.studio_api import ApiError, _read_state, _write_failed

ROOT = Path(__file__).resolve().parents[2]


class OfflineRetryTest(unittest.TestCase):
    def test_failed_offline_install_can_be_withdrawn_for_reupload(self):
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

            self.assertEqual(offline.delete_package("supply-chain", "admin"),
                             {"sample": "supply-chain", "deleted": True})
            self.assertFalse(destination.exists())
            self.assertFalse((state / "supply-chain.json").exists())

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

                with self.assertRaises(ApiError):
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
