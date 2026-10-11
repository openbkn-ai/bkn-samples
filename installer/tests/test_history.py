import tempfile
import unittest
from pathlib import Path

from installer.history import read_installation_history, record_terminal_installation


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

            self.assertTrue(complete)
            self.assertEqual([item["version"] for item in items], ["0.1.1", "0.1.0"])


if __name__ == "__main__":
    unittest.main()
