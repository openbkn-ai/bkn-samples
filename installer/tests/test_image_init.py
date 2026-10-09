import os
import subprocess
import tempfile
import unittest
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[2] / "installer/image/10-bkn-sample-init.sh"


class ImageInitTest(unittest.TestCase):
    def manifest(self, root, directory, sample_id, hook="db/init.sh"):
        folder = root / directory
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "sample.yaml").write_text(
            "apiVersion: samples.openbkn.ai/v1alpha1\nkind: Sample\n"
            f"metadata:\n  name: {sample_id}\nspec:\n  hooks:\n    dbInit: {hook}\n")

    def test_loads_as_root_even_when_the_entrypoint_exports_the_app_user(self):
        root = Path(tempfile.mkdtemp())
        db = root / "supply_ontology_hand" / "db"
        db.mkdir(parents=True)
        self.manifest(root, "supply_ontology_hand", "supply-chain")
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

    def test_world_cup_cache_is_created_where_the_database_user_can_write(self):
        root = Path(tempfile.mkdtemp())
        cache_root = Path(tempfile.mkdtemp())
        db = root / "world-cup" / "db"
        db.mkdir(parents=True)
        self.manifest(root, "world-cup", "world-cup")
        init = db / "init.sh"
        init.write_text('#!/bin/sh\ntest -d "$BKN_SAMPLE_CACHE" && printf "%s" "$BKN_SAMPLE_CACHE"\n')
        init.chmod(0o755)
        env = {
            "PATH": os.environ["PATH"],
            "BKN_SAMPLE_ID": "world-cup",
            "BKN_SAMPLE_ROOT": str(root),
            "TMPDIR": str(cache_root),
            "MYSQL_USER": "bkn_sample",
            "MARIADB_ROOT_PASSWORD": "root-password",
            "MARIADB_DATABASE": "worldcup",
        }
        result = subprocess.run(["sh", str(WRAPPER)], env=env, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, str(cache_root / "bkn-samples/cache/world-cup"))

    def test_selects_a_new_sample_and_its_declared_hook_without_a_dispatcher_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.manifest(root, "different-directory", "third-sample", "database/load.sh")
            hook = root / "different-directory/database/load.sh"
            hook.parent.mkdir()
            hook.write_text('#!/bin/sh\nprintf "third-sample"\n')
            hook.chmod(0o755)
            result = self.run_wrapper(root, "third-sample")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "third-sample")

    def run_wrapper(self, root, sample_id):
        return subprocess.run(["sh", str(WRAPPER)], capture_output=True, text=True, check=False,
                              env={"PATH": os.environ["PATH"], "BKN_SAMPLE_ROOT": str(root),
                                   "BKN_SAMPLE_ID": sample_id, "TMPDIR": str(root)})

    def test_rejects_unknown_duplicate_escaped_and_symlink_hooks(self):
        for case in ("unknown", "duplicate", "escape", "symlink"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.manifest(root, "one", "third-sample",
                              "../outside.sh" if case == "escape" else "db/init.sh")
                hook = root / "one/db/init.sh"
                hook.parent.mkdir()
                hook.write_text('#!/bin/sh\nexit 0\n')
                hook.chmod(0o755)
                if case == "duplicate":
                    self.manifest(root, "two", "third-sample")
                    other = root / "two/db/init.sh"
                    other.parent.mkdir()
                    other.write_bytes(hook.read_bytes())
                if case == "symlink":
                    target = root / "outside.sh"
                    hook.rename(target)
                    hook.symlink_to(target)
                result = self.run_wrapper(root, "missing" if case == "unknown" else "third-sample")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Cannot select a safe database hook", result.stderr)


if __name__ == "__main__":
    unittest.main()
