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
    def test_cleaned_installation_uses_imported_package_even_when_bundled_release_matches(self):
        from installer.contract import sample_version
        from installer.offline_bundle import OfflinePackages
        from installer.control_plane import _write_state
        from installer.history import read_installation_history
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            index = build_manifest_index(ROOT, "a" * 40)
            bundled = next(item for item in index["samples"] if item["name"] == "supply-chain")
            version = sample_version(bundled)
            document = bundled["document"] if "document" in bundled else None
            if document is None:
                from installer.contract import load_sample
                document = load_sample(ROOT / "samples/supply_ontology_hand")
            release = {"sample": "supply-chain", "version": version,
                       "manifestSha256": bundled["manifestSha256"], "packageDigest": "sha256:" + "b" * 64,
                       "dataImageRef": "ghcr.io/openbkn-ai/bkn-samples@sha256:" + "c" * 64,
                       "releaseNotes": {"version": version, "documents": []}, "document": document}
            cache = state / "offline/supply-chain"
            cache.mkdir(parents=True)
            write_json(cache / "release.json", release)
            previous = {"id": "inst-old", "sample": "supply-chain", "version": version, "status": "uninstalled",
                        "historyComplete": True, "remoteRelease": {"entry": {"version": version}}}
            write_json(state / "supply-chain.json", previous)
            apps, runners = [], []
            def runner(*args):
                instance = InstallationRunner(*args)
                runners.append(instance)
                return instance
            def execute(_offline, selected, _install, retry=False):
                self.assertEqual(selected, release)
                self.assertFalse(retry)
                current = _read_state(state, "supply-chain")
                self.assertIn("offlineRelease", current)
                self.assertNotIn("remoteRelease", current)
                current.update(status="installed", finishedAt="2099-01-01T00:00:00Z")
                _write_state(state, current)
            env = {"BKN_SAMPLES_ROOT": str(ROOT), "BKN_SAMPLE_STATE_DIR": directory,
                   "BKN_SAMPLE_PLATFORM_VERSION": "0.2.0", "BKN_SAMPLE_CATALOG_URL": "",
                   "BKN_SAMPLE_EXECUTOR_IMAGE_REF": "ghcr.io/openbkn-ai/executor@sha256:" + "d" * 64}
            with patch.dict("os.environ", env), \
                 patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                 patch("installer.task_runner.InstallationRunner", side_effect=runner), \
                 patch("installer.studio_api.load_indexes", return_value=(read_version(ROOT), index, index)), \
                 patch.object(OfflinePackages, "execute", execute), \
                 patch("installer.remote_installation.RemoteInstallation.execute") as remote, \
                 patch("installer.catalog_source.read_url") as network:
                main()
                apps[0].authenticate = lambda _: "admin"
                status, _ = dispatch(apps[0], "POST", "/api/studio/samples/supply-chain/installations", "Bearer test",
                                     json.dumps({"version": version, "manifestSha256": release["manifestSha256"]}).encode())
                self.assertEqual(status, 202)
                self.assertTrue(runners[0].locks["supply-chain"].acquire(timeout=2))
                runners[0].locks["supply-chain"].release()
                new = _read_state(state, "supply-chain")
                self.assertEqual(new["status"], "installed")
                self.assertNotEqual(new["id"], previous["id"])
                history, _ = read_installation_history(state, "supply-chain", new)
                self.assertIn(previous, history)
                remote.assert_not_called()
                network.assert_not_called()

    @patch("installer.executor_compatibility.cli_capabilities", return_value=True)
    def test_default_directory_exposes_published_versions_without_a_refresh(self, _sdk):
        for platform_version in ("0.2.0", read_version(ROOT)):
            with self.subTest(platform_version=platform_version):
                apps = []
                with tempfile.TemporaryDirectory() as directory:
                    index = build_manifest_index(ROOT, "a" * 40)
                    index["samples"] = [s for s in index["samples"] if s["name"] in {"supply-chain", "world-cup"}]
                    env = {"BKN_SAMPLES_ROOT": str(ROOT), "BKN_SAMPLE_STATE_DIR": directory,
                           "BKN_SAMPLE_PLATFORM_VERSION": platform_version, "BKN_SAMPLE_PLATFORM_CAPABILITIES": "",
                           "BKN_SAMPLE_CATALOG_URL": "",
                           "BKN_SAMPLE_EXECUTOR_IMAGE_REF": "ghcr.io/openbkn-ai/bkn-sample-studio@sha256:" + "d" * 64}
                    with patch.dict("os.environ", env), \
                         patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                         patch("installer.studio_api.load_indexes", return_value=(read_version(ROOT), index, index)), \
                         patch("installer.catalog_source.read_url") as network:
                        main()
                        catalog = apps[0].catalog("admin")
                    entries = json.loads((ROOT / "catalogs" / platform_version / "catalog.json").read_text())["spec"]["entries"]
                    published = {e["sampleId"]: e for e in sorted(entries, key=lambda e: tuple(map(int, e["version"].split(".")))) if e["releaseStatus"] == "published"}
                    self.assertEqual({c["name"]: c["version"] for c in catalog["samples"]},
                                     {name: entry["version"] for name, entry in published.items()})
                    for card in catalog["samples"]:
                        # Discovery includes releases requiring a newer platform; install must retain the floor.
                        floor = published[card["name"]]["requires"]["platformVersion"].split()[0].removeprefix(">=")
                        supports = tuple(map(int, platform_version.split("."))) >= tuple(map(int, floor.split(".")))
                        self.assertEqual(card["installable"], supports, card["name"])
                        if not supports:
                            selected = next(v for v in card["versions"] if v["version"] == card["version"])
                            self.assertEqual(selected["reason"], "runtime_upgrade_required")
                    self.assertIsNone(catalog["sourceRefresh"]["lastSuccessfulRefreshAt"])
                    network.assert_not_called()

    def test_unlisted_bundled_sample_cannot_bypass_product_directory(self):
        apps = []
        with tempfile.TemporaryDirectory() as directory:
            index = build_manifest_index(ROOT, "a" * 40)
            env = {"BKN_SAMPLES_ROOT": str(ROOT), "BKN_SAMPLE_STATE_DIR": directory,
                   "BKN_SAMPLE_PLATFORM_VERSION": "0.2.1", "BKN_SAMPLE_CATALOG_URL": ""}
            with patch.dict("os.environ", env), \
                 patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                 patch("installer.studio_api.load_indexes", return_value=(read_version(ROOT), index, index)), \
                 patch("installer.runtime.install_sample") as install:
                main()
                apps[0].authenticate = lambda _: "admin"
                status, payload = dispatch(apps[0], "POST", "/api/studio/samples/supply-chain/installations", "Bearer test", b"{}")
                self.assertEqual(status, 409)
                self.assertEqual(payload["code"], "source_rejected")
                install.assert_not_called()
                self.assertFalse((Path(directory) / "supply-chain.json").exists())

    def test_offline_import_uses_the_same_automatic_runtime_defaults(self):
        from tools.publication.build_candidate import build
        from installer.studio_api import ApiError

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory).resolve()
            from installer.tests.test_offline_image import image_fixture
            ref, _ = image_fixture(temporary / "oci")
            candidate = build(ROOT / "samples/supply_ontology_hand", "0.1.2", temporary / "candidate", ref, temporary / "oci")
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
                 patch("installer.platform_version.read_backend_version", return_value=read_version(ROOT)) as health:
                main()
                result = apps[0].import_package(candidate / "package.tar.gz", "admin")
                self.assertEqual(result["version"], "0.1.2")
                health.assert_called_with("http://gateway.example")
                self.assertFalse((state / "supply-chain.json").exists())
                health.return_value = ""
                with self.assertRaises(ApiError):
                    apps[0].import_package(candidate / "package.tar.gz", "admin")
                self.assertFalse((state / "supply-chain.json").exists())
                health.return_value = read_version(ROOT)
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
