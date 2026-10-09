import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.state_store import write_json
from installer.studio_api import _read_state, _write_installing
from installer.studio_http import dispatch, main

ROOT = Path(__file__).resolve().parents[2]


class AsyncHttpTest(unittest.TestCase):
    def test_create_and_retry_return_accepted_before_runtime_finishes(self):
        for retry in (False, True):
            with self.subTest(retry=retry), tempfile.TemporaryDirectory() as directory:
                state = Path(directory)
                _write_installing(state, "supply-chain", "0.1.0")
                if retry:
                    record = _read_state(state, "supply-chain")
                    record["status"] = "failed"
                    record["stages"] = {"database": "succeeded", "verify": "failed"}
                    write_json(state / "supply-chain.json", record)
                else:
                    (state / "supply-chain.json").unlink()
                apps, calls = [], []
                gate, started, finished = threading.Event(), threading.Event(), threading.Event()
                def run(**kwargs):
                    calls.append(kwargs)
                    started.set()
                    gate.wait(5)
                    record = _read_state(state, "supply-chain")
                    record["status"] = "installed"
                    write_json(state / "supply-chain.json", record)
                    finished.set()
                env = {"BKN_SAMPLES_ROOT": str(ROOT), "BKN_SAMPLE_IMAGE_INDEX": str(ROOT / "manifest-index.json"),
                       "BKN_SAMPLE_STATE_DIR": str(state)}
                with patch.dict("os.environ", env), patch("installer.studio_http.serve", side_effect=lambda app, *args: apps.append(app)), \
                     patch("installer.runtime.install_sample", side_effect=run), patch("installer.runtime.retry_sample", side_effect=run):
                    main()
                    app = apps[0]
                    app.authenticate = lambda _: "admin"
                    route = "/api/studio/samples/supply-chain/installations" + ("/inst-supply-chain/retry" if retry else "")
                    try:
                        status, payload = dispatch(app, "POST", route, "Bearer private-test-token", b"{}")
                        self.assertEqual(status, 202)
                        self.assertEqual(payload["status"], "installing")
                        self.assertTrue(started.wait(1))
                        self.assertFalse(finished.is_set())
                        self.assertEqual(_read_state(state, "supply-chain")["status"], "installing")
                        duplicate, _ = dispatch(app, "POST", route, "Bearer private-test-token", b"{}")
                        self.assertEqual(duplicate, 409)
                        self.assertEqual(len(calls), 1)
                        self.assertEqual(calls[0]["authorization"], "Bearer private-test-token")
                        if retry:
                            self.assertTrue(calls[0]["accepted"])
                        self.assertNotIn("private-test-token", (state / "supply-chain.json").read_text())
                        self.assertEqual(dispatch(app, "GET", "/api/studio/samples/supply-chain/installations/inst-supply-chain", "Bearer t", b"")[1]["status"], "installing")
                    finally:
                        gate.set()
                        self.assertTrue(finished.wait(2))


if __name__ == "__main__":
    unittest.main()
