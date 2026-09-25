import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from installer.runtime import database_config, install_sample, retry_sample
from installer.studio_api import ApiError

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "secret-password"


def completed(stdout: str = "", code: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


class RuntimeTest(unittest.TestCase):
    def test_install_passes_the_secret_to_the_hook_and_hides_it(self):
        seen = {}

        def deploy(_sample):
            return {
                "service": "bkn-sample-supply-chain",
                "namespace": "openbkn-samples",
                "host": "bkn-sample-supply-chain.openbkn-samples.svc",
                "port": 3306,
                "database": "supply_demo_hand",
                "user": "bkn_sample",
            }

        def kubectl(_args, stdin=None):
            return completed(base64.b64encode(PASSWORD.encode("utf-8")).decode("ascii"))

        def run(argv, env):
            if argv[0] == "openbkn":
                seen["token"] = (env or {}).get("BKN_TOKEN")
                if "resources" in argv:
                    return completed(json.dumps({"entries": [{}] * 12}))
                if "list" in argv:
                    return completed(json.dumps({"entries": []}))
                return completed(json.dumps({"id": "cat-1", "name": "bkn-sample-supply-chain"}))
            payload = json.loads(Path(env["BKN_SAMPLE_INPUT"]).read_text(encoding="utf-8"))
            seen["password"] = payload["database"]["password"]
            seen["network"] = payload["knowledgeNetwork"]["id"]
            seen["hook_token"] = env.get("BKN_TOKEN")
            Path(env["BKN_SAMPLE_OUTPUT"]).write_text(json.dumps({"ok": True, "resources": {}}), encoding="utf-8")
            return completed()

        view = install_sample(
            sample="supply-chain",
            actor_role="admin",
            state_dir=Path(tempfile.mkdtemp()),
            root=ROOT,
            version="0.1.0",
            deploy=deploy,
            kubectl=kubectl,
            run=run,
            authorization="Bearer admin-token",
        )
        self.assertEqual(seen["password"], PASSWORD)
        self.assertEqual(seen["network"], "supply_ontology_hand")
        self.assertEqual(seen["token"], "admin-token")
        self.assertEqual(seen["hook_token"], "admin-token")
        self.assertEqual(view["status"], "installed")
        rendered = json.dumps(view)
        self.assertNotIn(PASSWORD, rendered)
        self.assertNotIn("admin-token", rendered)

    def test_user_retry_does_not_deploy(self):
        state = Path(tempfile.mkdtemp())
        (state / "supply-chain.json").write_text(
            json.dumps({"id": "inst-supply-chain", "sample": "supply-chain", "status": "failed", "stages": {}}),
            encoding="utf-8",
        )
        calls = {"deploy": 0}

        def deploy(_sample):
            calls["deploy"] += 1

        with self.assertRaises(ApiError) as caught:
            retry_sample(
                sample="supply-chain",
                installation_id="inst-supply-chain",
                actor_role="user",
                state_dir=state,
                root=ROOT,
                version="0.1.0",
                deploy=deploy,
                kubectl=lambda *_args, **_kwargs: completed(),
                run=lambda *_args, **_kwargs: completed(),
            )
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(calls["deploy"], 0)

    def test_database_config_reads_the_secret(self):
        config = database_config(
            {"service": "bkn-sample-supply-chain", "namespace": "openbkn-samples", "host": "db", "port": 3306, "database": "supply_demo_hand", "user": "bkn_sample"},
            lambda _args: completed(base64.b64encode(b"secret").decode("ascii")),
        )
        self.assertEqual(config["password"], "secret")


if __name__ == "__main__":
    unittest.main()
