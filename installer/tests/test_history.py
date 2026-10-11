import tempfile
import unittest
from pathlib import Path

from installer.history import begin_installation_attempt, read_installation_history, record_terminal_installation


class InstallationHistoryTest(unittest.TestCase):
    def test_keeps_terminal_records_for_multiple_versions(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            record_terminal_installation(state, {
                "id": "inst-supply-chain", "sample": "supply-chain", "version": "0.1.0",
                "status": "installed", "finishedAt": "2026-10-10T00:00:00Z",
            })
            record_terminal_installation(state, {
                "id": "inst-supply-chain", "sample": "supply-chain", "version": "0.1.1",
                "status": "failed", "finishedAt": "2026-10-10T01:00:00Z",
            })

            items, complete = read_installation_history(state, "supply-chain", None)

            self.assertFalse(complete)
            self.assertEqual([item["version"] for item in items], ["0.1.1", "0.1.0"])

    def test_same_version_attempts_are_distinct_and_archiving_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            first = {"id": "inst-demo", "sample": "demo", "version": "0.1.0", "status": "installing"}
            begin_installation_attempt(state, first, None)
            first.update(status="failed", finishedAt="2026-10-10T00:00:00Z")
            record_terminal_installation(state, first)
            record_terminal_installation(state, first)
            record_terminal_installation(state, {**first, "error": {"code": "changed"}})
            retry = {**first, "status": "installing"}
            begin_installation_attempt(state, retry, first)
            self.assertNotEqual(first["attemptId"], retry["attemptId"])
            self.assertNotEqual(first["startedAt"], retry["startedAt"])
            self.assertNotIn("finishedAt", retry)
            retry.update(status="installed", finishedAt="2026-10-10T01:00:00Z")
            record_terminal_installation(state, retry)
            items, complete = read_installation_history(state, "demo", retry)
            self.assertTrue(complete)
            self.assertEqual([item["status"] for item in items], ["installed", "failed"])
            self.assertEqual(items[1], first)
            self.assertEqual(len(list((state / "history/demo").glob("*.json"))), 2)

    def test_retry_preserves_legacy_result_and_incomplete_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            legacy = {"id": "inst-demo", "sample": "demo", "version": "0.1.0", "status": "failed"}
            retry = {**legacy, "status": "installing"}
            begin_installation_attempt(state, retry, legacy)
            retry.update(status="installed", finishedAt="2026-10-10T01:00:00Z")
            record_terminal_installation(state, retry)
            items, complete = read_installation_history(state, "demo", retry)
            self.assertFalse(complete)
            self.assertEqual(len(items), 2)
            self.assertIn(legacy, items)

    def test_corrupt_archive_does_not_claim_complete_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            record = {"id": "inst-demo", "sample": "demo", "version": "0.1.0", "status": "installing"}
            begin_installation_attempt(state, record, None)
            record["status"] = "installed"
            record_terminal_installation(state, record)
            (state / "history/demo/broken.json").write_text("{")
            items, complete = read_installation_history(state, "demo", record)
            self.assertEqual(len(items), 1)
            self.assertFalse(complete)


if __name__ == "__main__":
    unittest.main()
