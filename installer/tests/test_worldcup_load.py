import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOAD = _load("load_worldcup", "samples/world-cup/db/load_worldcup.py")
INSTALL = _load("install_worldcup", "samples/world-cup/platform/install_worldcup.py")
VERIFY = _load("verify_worldcup_platform", "samples/world-cup/platform/verify_worldcup.py")


class _Body:
    def read(self, _size):
        if self._sent:
            return b""
        self._sent = True
        return b"not-the-locked-bytes"

    def __init__(self):
        self._sent = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class WorldCupLoadTest(unittest.TestCase):
    def test_wide_tables_use_varchar_255(self):
        wide = LOAD.create_table_sql("wc_matches", ["match_id"])
        narrow = LOAD.create_table_sql("wc_teams", ["team_id"])
        self.assertIn("VARCHAR(255)", wide)
        self.assertIn("VARCHAR(512)", narrow)
        self.assertIn("VARCHAR(255)", LOAD.create_table_sql("wc_team_appearances", ["team_id"]))

    def test_checksum_mismatch_stops_before_the_database(self):
        with tempfile.TemporaryDirectory() as cache:
            previous = os.environ.get("BKN_SAMPLE_CACHE")
            os.environ["BKN_SAMPLE_CACHE"] = cache
            os.environ["BKN_SAMPLE_ID"] = "world-cup"
            os.environ["BKN_SAMPLE_VERSION"] = "0.1.0"
            os.environ["MYSQL_DATABASE"] = "worldcup"
            os.environ.pop("MYSQL_USER", None)
            try:
                with self.assertRaises(SystemExit) as caught:
                    LOAD.load_worldcup(opener=lambda *_args, **_kwargs: _Body())
            finally:
                if previous is None:
                    os.environ.pop("BKN_SAMPLE_CACHE", None)
                else:
                    os.environ["BKN_SAMPLE_CACHE"] = previous
        self.assertIn("checksum mismatch", str(caught.exception))

    def test_missing_embedding_is_recorded_and_install_still_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {
                "sample": "world-cup",
                "catalog": {"id": "cat-1", "name": "bkn-sample-world-cup"},
                "database": {
                    "host": "db.example",
                    "port": 3306,
                    "name": "worldcup",
                    "user": "bkn_sample",
                    "password": "secret",
                },
            }
            source = root / "input.json"
            output = root / "output.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            os.environ["BKN_SAMPLE_INPUT"] = str(source)
            os.environ["BKN_SAMPLE_OUTPUT"] = str(output)
            os.environ["BKN_SAMPLE_PRINT_ONLY"] = "1"
            os.environ["BKN_SAMPLE_EMBEDDING"] = "0"
            os.environ["EMBEDDING_MODEL_NAME"] = "text-embedding-v4-cn"
            try:
                self.assertEqual(INSTALL.main(), 0)
            finally:
                os.environ.pop("BKN_SAMPLE_PRINT_ONLY", None)
                os.environ.pop("BKN_SAMPLE_EMBEDDING", None)
            body = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(body["ok"])
        self.assertEqual(body["degrade"][0]["code"], "keyword-index")
        self.assertEqual(body["resources"]["knowledgeNetworkId"], "worldcup_vega_catalog_bkn")

    def test_verify_reads_the_hook_database(self):
        saved = {key: os.environ.get(key) for key in ("MYSQL_HOST", "MYSQL_UNIX_SOCKET", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE", "MYSQL_PORT")}
        for key in saved:
            os.environ.pop(key, None)
        try:
            VERIFY.apply_database_env(
                {
                    "sample": "world-cup",
                    "version": "0.1.0",
                    "database": {
                        "host": "db.example",
                        "port": 3306,
                        "name": "worldcup",
                        "user": "bkn_sample",
                        "password": "secret",
                    },
                }
            )
            self.assertEqual(os.environ["MYSQL_HOST"], "db.example")
            self.assertEqual(os.environ["MYSQL_DATABASE"], "worldcup")
            self.assertEqual(os.environ["MYSQL_USER"], "bkn_sample")
            self.assertEqual(os.environ["BKN_SAMPLE_VERSION"], "0.1.0")
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_database_success_does_not_mark_the_tool_ready(self):
        checks = VERIFY.build_checks(data_ok=True, tool_ok=False)
        by_name = {item["name"]: item["ok"] for item in checks}
        self.assertTrue(by_name["tables-discovered"])
        self.assertTrue(by_name["cross-table-query"])
        self.assertFalse(by_name["capability-callable"])
        self.assertNotIn("skill-discoverable", by_name)


if __name__ == "__main__":
    unittest.main()
