import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.studio_api import _read_state
from installer.state_store import write_json
from installer.studio_http import main, dispatch
from installer.task_runner import InstallationRunner
from installer.tests import test_remote_bundle as bundle_fixture

ROOT = bundle_fixture.ROOT


class RemoteHttpTest(unittest.TestCase):
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
                   "BKN_SAMPLE_STATE_DIR": str(state), "BKN_SAMPLE_PLATFORM_VERSION": "0.2.0",
                   "BKN_SAMPLE_EXECUTOR_IMAGE_REF": "ghcr.io/openbkn-ai/bkn-sample-studio@sha256:" + "d" * 64,
                   "BKN_SAMPLE_PLATFORM_CAPABILITIES": ",".join(fixture.entry["requires"]["capabilities"])}
            with patch.dict("os.environ", env), patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                 patch("installer.catalog_source.OfficialCatalog.entries", return_value=[fixture.entry]), \
                 patch("installer.remote_installation.RemoteInstallation.execute", side_effect=execute), \
                 patch("installer.task_runner.InstallationRunner", side_effect=make_runner):
                main()
                app = apps[0]
                app.authenticate = lambda _: "admin"
                route = "/api/studio/samples/supply-chain/installations"
                body = json.dumps({"version": "1.0.0", "manifestSha256": fixture.entry["manifest"]["digest"][7:]}).encode()
                bad = json.dumps({"version": "1.0.0", "manifestSha256": "a" * 64}).encode()
                self.assertEqual(dispatch(app, "POST", route, "Bearer test-secret", bad)[0], 409)
                self.assertFalse((state / "supply-chain.json").exists())
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
