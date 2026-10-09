import json
import tempfile
import threading
import unittest
from pathlib import Path

from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, _write_installing
from installer.task_runner import InstallationRunner


class TaskRunnerTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name)
        self.runner = InstallationRunner(self.state, ["supply-chain"])

    def test_acceptance_is_persisted_before_work_completes_and_duplicates_are_blocked(self):
        gate, started, done = threading.Event(), threading.Event(), threading.Event()
        def execute():
            started.set()
            gate.wait(3)
            record = _read_state(self.state, "supply-chain")
            record["status"] = "installed"
            write_json(self.state / "supply-chain.json", record)
            done.set()
        try:
            accepted = self.runner.submit("supply-chain", lambda: _write_installing(self.state, "supply-chain", "0.1.0"), execute)
            self.assertTrue(started.wait(1))
            self.assertEqual(accepted["status"], "installing")
            self.assertEqual(_read_state(self.state, "supply-chain")["status"], "installing")
            self.assertFalse(done.is_set())
            with self.assertRaises(ApiError) as caught:
                self.runner.submit("supply-chain", lambda: self.fail("duplicate prepare"), execute)
            self.assertEqual(caught.exception.code, "already_installing")
        finally:
            gate.set()
            self.assertTrue(done.wait(2))

    def test_restart_marks_only_inflight_tasks_failed_and_keeps_snapshots(self):
        record = {"id": "inst-supply-chain", "sample": "supply-chain", "version": "0.1.0", "status": "installing",
                  "stages": {"database": "succeeded", "knowledge": "running"},
                  "manifestSha256": "fixed", "releaseNotesSnapshot": {"version": "0.1.0"}, "dataImageRef": "image@sha256:fixed"}
        write_json(self.state / "supply-chain.json", record)
        self.runner.recover_interrupted()
        recovered = _read_state(self.state, "supply-chain")
        self.assertEqual(recovered["error"]["code"], "install_interrupted")
        self.assertEqual(recovered["stages"], {"database": "succeeded", "knowledge": "failed"})
        for key in ["manifestSha256", "releaseNotesSnapshot", "dataImageRef"]:
            self.assertEqual(recovered[key], record[key])
        self.runner.recover_interrupted()
        self.assertEqual(_read_state(self.state, "supply-chain"), recovered)
        recovered["status"] = "installed"
        write_json(self.state / "supply-chain.json", recovered)
        self.runner.recover_interrupted()
        self.assertEqual(_read_state(self.state, "supply-chain"), recovered)

    def test_unexpected_worker_failure_is_private_and_lock_is_released(self):
        def execute():
            raise RuntimeError("password=private-secret token=private-token")
        self.runner.submit("supply-chain", lambda: _write_installing(self.state, "supply-chain", "0.1.0"), execute)
        self.assertTrue(self.runner.locks["supply-chain"].acquire(timeout=2))
        self.runner.locks["supply-chain"].release()
        record = _read_state(self.state, "supply-chain")
        self.assertEqual(record["status"], "failed")
        self.assertNotIn("private", json.dumps(record))
        self.assertEqual(record["stages"]["database"], "failed")

    def test_preflight_failure_does_not_start_work_or_change_success(self):
        write_json(self.state / "supply-chain.json", {"sample": "supply-chain", "status": "installed"})
        def prepare():
            raise ApiError(409, "already_installed", "already installed")
        with self.assertRaises(ApiError):
            self.runner.submit("supply-chain", prepare, lambda: self.fail("worker started"))
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "installed")
        self.assertFalse(self.runner.locks["supply-chain"].locked())


if __name__ == "__main__":
    unittest.main()
