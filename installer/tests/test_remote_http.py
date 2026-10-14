import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.studio_api import _read_state
from installer.contract import build_manifest_index, read_version
from installer.state_store import write_json
from installer.studio_http import main, dispatch
from installer.task_runner import InstallationRunner
from installer.tests import test_remote_bundle as bundle_fixture

ROOT = bundle_fixture.ROOT


class RemoteHttpTest(unittest.TestCase):
    def test_default_directory_exposes_published_versions_without_a_refresh(self):
        apps = []
        with tempfile.TemporaryDirectory() as directory:
            index = build_manifest_index(ROOT, "a" * 40)
            index["samples"] = [s for s in index["samples"] if s["name"] in {"supply-chain", "world-cup"}]
            env = {"BKN_SAMPLES_ROOT": str(ROOT), "BKN_SAMPLE_STATE_DIR": directory,
                   "BKN_SAMPLE_PLATFORM_VERSION": "0.2.0", "BKN_SAMPLE_PLATFORM_CAPABILITIES": "",
                   "BKN_SAMPLE_CATALOG_URL": "",
                   "BKN_SAMPLE_EXECUTOR_IMAGE_REF": "ghcr.io/openbkn-ai/bkn-sample-studio@sha256:" + "d" * 64}
            with patch.dict("os.environ", env), \
                 patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                 patch("installer.studio_api.load_indexes", return_value=(read_version(ROOT), index, index)), \
                 patch("installer.catalog_source.read_url") as network:
                main()
                catalog = apps[0].catalog("admin")
            entries = json.loads((ROOT / "catalog.json").read_text())["spec"]["entries"]
            expected = {e["sampleId"]: e["version"] for e in sorted(entries, key=lambda e: tuple(map(int, e["version"].split(".")))) if e["releaseStatus"] == "published"}
            self.assertEqual({c["name"]: c["version"] for c in catalog["samples"]}, expected)
            self.assertTrue(all(c["installable"] for c in catalog["samples"]))
            self.assertIsNone(catalog["sourceRefresh"]["lastSuccessfulRefreshAt"])
            network.assert_not_called()

    def test_offline_import_uses_the_same_automatic_runtime_defaults(self):
        from tools.publication.build_candidate import build
        from installer.studio_api import ApiError

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory).resolve()
            candidate = build(ROOT / "samples/supply_ontology_hand", "0.1.2", temporary / "candidate",
                              "ghcr.io/openbkn-ai/bkn-samples@sha256:" + "a" * 64)
            state = temporary / "state"
            env = {"BKN_SAMPLES_ROOT": str(ROOT), "BKN_SAMPLE_STATE_DIR": str(state),
                   "BKN_SAMPLE_IMAGE_INDEX": str(ROOT / "manifest-index.json"),
                   "BKN_BASE_URL": "http://gateway.example", "BKN_SAMPLE_PLATFORM_VERSION": "",
                   "BKN_SAMPLE_PLATFORM_CAPABILITIES": "",
                   "BKN_SAMPLE_EXECUTOR_IMAGE_REF": "ghcr.io/openbkn-ai/bkn-sample-studio@sha256:" + "d" * 64}
            apps = []
            with patch.dict("os.environ", env), \
                 patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                 patch("installer.studio_api.load_indexes", return_value=(read_version(ROOT), build_manifest_index(ROOT, "a" * 40), build_manifest_index(ROOT, "a" * 40))), \
                 patch("installer.platform_version.read_backend_version", return_value="0.2.0") as health:
                main()
                result = apps[0].import_package(candidate / "package.tar.gz", "admin")
                self.assertEqual(result["version"], "0.1.2")
                health.assert_called_with("http://gateway.example")
                self.assertFalse((state / "supply-chain.json").exists())
                health.return_value = ""
                with self.assertRaises(ApiError):
                    apps[0].import_package(candidate / "package.tar.gz", "admin")
                self.assertFalse((state / "supply-chain.json").exists())
                health.return_value = "0.2.0"
                with patch.dict("os.environ", {"BKN_SAMPLE_PLATFORM_CAPABILITIES": "vega.catalog"}):
                    main()
                    with self.assertRaises(ApiError):
                        apps[-1].import_package(candidate / "package.tar.gz", "admin")

    def test_http_accepts_fixed_release_before_worker_and_retries_original_after_restart(self):
        fixture = bundle_fixture.RemoteBundleTest("test_fixed_release_extracts_and_matches_existing_runtime_contract")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.load()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            gate, started, finished = threading.Event(), threading.Event(), threading.Event()
            calls, apps = [], []
            retried = threading.Event()
            runners = []
            def make_runner(*args):
                runner = InstallationRunner(*args)
                runners.append(runner)
                return runner
            def execute(sample, callback, retry=False):
                calls.append((sample, retry))
                if retry:
                    retried.set()
                started.set()
                gate.wait(5)
                current = _read_state(state, sample)
                current["status"] = "failed"
                current["error"] = {"code": "install_failed", "message": "test failure"}
                write_json(state / f"{sample}.json", current)
                finished.set()
            env = {"BKN_SAMPLES_ROOT": str(ROOT), "BKN_SAMPLE_IMAGE_INDEX": str(ROOT / "manifest-index.json"),
                   "BKN_SAMPLE_STATE_DIR": str(state), "BKN_SAMPLE_PLATFORM_VERSION": "",
                   "BKN_BASE_URL": "http://gateway.example",
                   "BKN_SAMPLE_EXECUTOR_IMAGE_REF": "ghcr.io/openbkn-ai/bkn-sample-studio@sha256:" + "d" * 64,
                   "BKN_SAMPLE_PLATFORM_CAPABILITIES": ""}
            with patch.dict("os.environ", env), patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                 patch("installer.studio_api.load_indexes", return_value=(read_version(ROOT), build_manifest_index(ROOT, "a" * 40), build_manifest_index(ROOT, "a" * 40))), \
                 patch("installer.catalog_source.OfficialCatalog.entries", return_value=[fixture.entry]), \
                 patch("installer.remote_installation.RemoteInstallation.execute", side_effect=execute), \
                 patch("installer.task_runner.InstallationRunner", side_effect=make_runner), \
                 patch("installer.platform_version.read_backend_version", return_value="0.2.0") as health:
                main()
                app = apps[0]
                app.authenticate = lambda _: "admin"
                route = "/api/studio/samples/supply-chain/installations"
                body = json.dumps({"version": "1.0.0", "manifestSha256": fixture.entry["manifest"]["digest"][7:]}).encode()
                bad = json.dumps({"version": "1.0.0", "manifestSha256": "a" * 64}).encode()
                self.assertEqual(dispatch(app, "POST", route, "Bearer test-secret", bad)[0], 409)
                self.assertFalse((state / "supply-chain.json").exists())
                health.assert_called_with("http://gateway.example")
                try:
                    health.return_value = ""
                    self.assertEqual(dispatch(app, "POST", route, "Bearer test-secret", body)[0], 409)
                    self.assertFalse((state / "supply-chain.json").exists())
                finally:
                    health.return_value = "0.2.0"
                supported = fixture.entry["requires"]["capabilities"]
                try:
                    fixture.entry["requires"]["capabilities"] = ["unknown.standard.api"]
                    self.assertEqual(dispatch(app, "POST", route, "Bearer test-secret", body)[0], 409)
                    self.assertFalse((state / "supply-chain.json").exists())
                finally:
                    fixture.entry["requires"]["capabilities"] = supported
                try:
                    status, view = dispatch(app, "POST", route, "Bearer test-secret", body)
                    self.assertEqual(status, 202)
                    self.assertEqual(view["version"], "1.0.0")
                    self.assertTrue(started.wait(1))
                    self.assertFalse(finished.is_set())
                    self.assertEqual(dispatch(app, "POST", route, "Bearer test-secret", body)[0], 409)
                    self.assertNotIn("test-secret", (state / "supply-chain.json").read_text())
                finally:
                    gate.set()
                    self.assertTrue(finished.wait(2))
                    self.assertTrue(runners[0].locks["supply-chain"].acquire(timeout=2))
                    runners[0].locks["supply-chain"].release()
                finished.clear()
                with patch("installer.catalog_source.OfficialCatalog.entries", return_value=[]):
                    main()
                    app = apps[-1]
                    app.authenticate = lambda _: "admin"
                    status, view = dispatch(app, "POST", route + "/inst-supply-chain/retry", "Bearer test-secret", b"{}")
                    self.assertEqual(status, 202)
                    self.assertEqual(view["version"], "1.0.0")
                self.assertTrue(retried.wait(1))
                self.assertTrue(finished.wait(2))
                self.assertTrue(runners[-1].locks["supply-chain"].acquire(timeout=2))
                runners[-1].locks["supply-chain"].release()
                self.assertEqual(calls[-1], ("supply-chain", True))


if __name__ == "__main__":
    unittest.main()
