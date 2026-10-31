import json
import tempfile
import threading
import unittest
from pathlib import Path

from installer.state_store import write_json
from installer.control_plane import _write_state
from installer.history import read_installation_history
from installer.studio_api import ApiError, _read_state, _write_failed, _write_installing
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

    def test_successful_callback_preserves_terminal_record_and_stages(self):
        expected = {}
        def execute():
            record = _read_state(self.state, "supply-chain")
            record.update(status="installed", stages={"database": "succeeded", "discover": "running"})
            _write_state(self.state, record)
            expected.update(record)
        self.runner.submit("supply-chain", lambda: _write_installing(self.state, "supply-chain", "0.1.0"), execute)
        self.assertTrue(self.runner.locks["supply-chain"].acquire(timeout=2))
        self.runner.locks["supply-chain"].release()
        self.assertEqual(_read_state(self.state, "supply-chain"), expected)
        history, _ = read_installation_history(self.state, "supply-chain", None)
        self.assertEqual(history, [expected])

    def test_persisted_business_failure_survives_callback_return_or_exception(self):
        for raises in (False, True):
            with self.subTest(raises=raises):
                expected = {}
                def execute():
                    record = _read_state(self.state, "supply-chain")
                    record.update(status="failed", stages={"database": "succeeded", "discover": "failed"},
                                  error={"code": "discover_incomplete", "message": "discovered 2 tables, expected 3"})
                    _write_state(self.state, record)
                    expected.update(record)
                    if raises:
                        raise ApiError(500, "discover_incomplete", record["error"]["message"])
                self.runner.submit("supply-chain", lambda: _write_installing(self.state, "supply-chain", "0.1.0"), execute)
                self.assertTrue(self.runner.locks["supply-chain"].acquire(timeout=2))
                self.runner.locks["supply-chain"].release()
                self.assertEqual(_read_state(self.state, "supply-chain"), expected)
                history, _ = read_installation_history(self.state, "supply-chain", None)
                self.assertIn(expected, history)

    def test_callback_without_terminal_status_fails_instead_of_remaining_inflight(self):
        def execute():
            record = _read_state(self.state, "supply-chain")
            record["stages"] = {"database": "succeeded", "discover": "running"}
            write_json(self.state / "supply-chain.json", record)
        self.runner.submit("supply-chain", lambda: _write_installing(self.state, "supply-chain", "0.1.0"), execute)
        self.assertTrue(self.runner.locks["supply-chain"].acquire(timeout=2))
        self.runner.locks["supply-chain"].release()
        record = _read_state(self.state, "supply-chain")
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["stages"], {"database": "succeeded", "discover": "failed"})
        self.assertEqual(record["error"]["code"], "install_failed")
        self.assertIn("returned without a terminal status", record["error"]["message"])
        history, _ = read_installation_history(self.state, "supply-chain", None)
        self.assertEqual(history, [record])

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
        history, _ = read_installation_history(self.state, "supply-chain", None)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], recovered)
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
        history, _ = read_installation_history(self.state, "supply-chain", None)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], record)

    def test_preflight_failure_does_not_start_work_or_change_success(self):
        write_json(self.state / "supply-chain.json", {"sample": "supply-chain", "status": "installed"})
        def prepare():
            raise ApiError(409, "already_installed", "already installed")
        with self.assertRaises(ApiError):
            self.runner.submit("supply-chain", prepare, lambda: self.fail("worker started"))
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "installed")
        self.assertNotIn("attemptId", _read_state(self.state, "supply-chain"))
        self.assertFalse((self.state / "history").exists())
        self.assertFalse(self.runner.locks["supply-chain"].locked())

    def test_failed_attempt_and_successful_retry_remain_in_history(self):
        sample = "supply-chain"
        def fail():
            raise RuntimeError("test failure")
        self.runner.submit(sample, lambda: _write_installing(self.state, sample, "0.1.0"), fail)
        self.assertTrue(self.runner.locks[sample].acquire(timeout=2))
        self.runner.locks[sample].release()
        first = _read_state(self.state, sample)
        def prepare_retry():
            current = _read_state(self.state, sample)
            current["status"] = "installing"
            write_json(self.state / f"{sample}.json", current)
        def succeed():
            current = _read_state(self.state, sample)
            current.update(status="installed", finishedAt="2099-01-01T00:00:00Z")
            _write_state(self.state, current)
        self.runner.submit(sample, prepare_retry, succeed)
        self.assertTrue(self.runner.locks[sample].acquire(timeout=2))
        self.runner.locks[sample].release()
        history, complete = read_installation_history(self.state, sample, _read_state(self.state, sample))
        self.assertTrue(complete)
        self.assertEqual([item["status"] for item in history], ["installed", "failed"])
        self.assertEqual(history[1], first)

    def test_database_failure_writer_preserves_attempt_identity(self):
        sample = "supply-chain"
        self.runner.submit(sample, lambda: _write_installing(self.state, sample, "0.1.0"),
                           lambda: _write_failed(self.state, sample, "0.1.0", "image_unavailable", "image unavailable"))
        self.assertTrue(self.runner.locks[sample].acquire(timeout=2))
        self.runner.locks[sample].release()
        current = _read_state(self.state, sample)
        self.assertTrue(current["attemptId"])
        history, complete = read_installation_history(self.state, sample, current)
        self.assertTrue(complete)
        self.assertEqual(history, [current])


if __name__ == "__main__":
    unittest.main()
