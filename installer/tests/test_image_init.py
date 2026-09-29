import os
import subprocess
import tempfile
import unittest
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[2] / "installer/image/10-bkn-sample-init.sh"


class ImageInitTest(unittest.TestCase):
    def test_loads_as_root_even_when_the_entrypoint_exports_the_app_user(self):
        root = Path(tempfile.mkdtemp())
        db = root / "supply_ontology_hand" / "db"
        db.mkdir(parents=True)
        init = db / "init.sh"
        init.write_text('#!/bin/sh\nprintf "%s:%s:%s" "$MYSQL_USER" "$MYSQL_PASSWORD" "$MYSQL_DATABASE"\n')
        init.chmod(0o755)
        env = {
            "PATH": os.environ["PATH"],
            "BKN_SAMPLE_ID": "supply-chain",
            "BKN_SAMPLE_ROOT": str(root),
            "BKN_SAMPLE_VERSION": "0.1.0",
            "MYSQL_USER": "bkn_sample",
            "MYSQL_PASSWORD": "app-password",
            "MARIADB_ROOT_PASSWORD": "root-password",
            "MARIADB_DATABASE": "supply_demo_hand",
        }
        result = subprocess.run(["sh", str(WRAPPER)], env=env, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "root:root-password:supply_demo_hand")


if __name__ == "__main__":
    unittest.main()
