import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_TOOLS = Path(__file__).resolve().parents[2] / "samples/supply_ontology_hand/tools"
sys.path.insert(0, str(_TOOLS))
_PATH = _TOOLS / "setup_catalog.py"
_SPEC = importlib.util.spec_from_file_location("setup_catalog", _PATH)
SETUP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(SETUP)


class SetupCatalogSecretTest(unittest.TestCase):
    def test_command_failure_does_not_keep_the_database_password(self):
        password = "db-secret-value"

        def run(args, **_kwargs):
            self.assertIn(password, " ".join(args))
            return type("Proc", (), {"returncode": 1, "stdout": "", "stderr": f"refused {password}"})()

        args = [
            "openbkn",
            "vega",
            "catalog",
            "create",
            "--connector-config",
            '{"host":"db","password":"%s"}' % password,
        ]
        with patch.object(SETUP.subprocess, "run", run):
            with self.assertRaises(RuntimeError) as caught:
                SETUP.run_cmd(args)
        message = str(caught.exception)
        self.assertNotIn(password, message)
        self.assertIn('"password":"***"', message)
        self.assertIn("refused ***", message)


if __name__ == "__main__":
    unittest.main()
