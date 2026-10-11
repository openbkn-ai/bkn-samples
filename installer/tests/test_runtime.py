import base64
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from installer.control_plane import ControlError
from installer.runtime import database_config, install_sample, openbkn_json, retry_sample, run_platform_hook
from installer.studio_api import ApiError

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = "secret-password"


def completed(stdout: str = "", code: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


class RuntimeTest(unittest.TestCase):
    def test_hook_keeps_a_structured_failure_without_a_code(self):
        def run(_argv, env):
            Path(env["BKN_SAMPLE_OUTPUT"]).write_text(
                json.dumps({"ok": False, "code": "", "message": "import_kn.py failed"}),
                encoding="utf-8",
            )
            return completed(code=1)

        result = run_platform_hook(
            ROOT, "platform-install", {"sample": "supply-chain"}, run
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["message"], "import_kn.py failed")

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
                "image": "ghcr.io/openbkn-ai/bkn-samples@sha256:" + "a" * 64,
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
            seen.setdefault("configs", []).append(env.get("BKN_SAMPLE_CONFIG"))
            seen["recorded_image"] = json.loads((Path(env["BKN_SAMPLE_CONFIG"]).parents[1] / "supply-chain.json").read_text())["dataImageRef"]
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
        self.assertEqual(seen["recorded_image"], "ghcr.io/openbkn-ai/bkn-samples@sha256:" + "a" * 64)
        self.assertEqual(seen["password"], PASSWORD)
        self.assertEqual(seen["network"], "supply_ontology_hand")
        self.assertEqual(seen["token"], "admin-token")
        self.assertEqual(seen["hook_token"], "admin-token")
        self.assertEqual(len(seen["configs"]), 2)
        self.assertTrue(seen["configs"][0])
        self.assertEqual(seen["configs"][0], seen["configs"][1])
        self.assertNotIn(PASSWORD, Path(seen["configs"][0]).read_text(encoding="utf-8") if Path(seen["configs"][0]).is_file() else "")
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

    def test_cli_failure_keeps_the_reason_and_drops_the_password(self):
        def run(_argv, _env):
            return subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr='Request failed: invalid tag\n{"password":"secret-value"}',
            )

        with self.assertRaises(ControlError) as caught:
            openbkn_json(["vega", "catalog", "list"], run)
        self.assertIn("invalid tag", caught.exception.message)
        self.assertNotIn("secret-value", caught.exception.message)

    def test_cli_null_body_is_an_empty_success(self):
        def run(_argv, _env):
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="null\n", stderr="")

        self.assertEqual(openbkn_json(["vega", "catalog", "enable", "catalog-id"], run), {})

    def test_hook_keeps_an_ownership_code_when_the_script_exits(self):
        def run(_argv, env):
            Path(env["BKN_SAMPLE_OUTPUT"]).write_text(
                json.dumps(
                    {
                        "ok": False,
                        "code": "ownership_conflict",
                        "message": "knowledge network already exists and is not managed by this installer",
                    }
                ),
                encoding="utf-8",
            )
            return completed(code=1)

        result = run_platform_hook(
            ROOT,
            "platform-install",
            {"sample": "supply-chain", "version": "0.1.0"},
            run,
            env={},
            state_dir=Path(tempfile.mkdtemp()),
        )
        self.assertEqual(result["code"], "ownership_conflict")

    def test_database_config_reads_the_secret(self):
        config = database_config(
            {"service": "bkn-sample-supply-chain", "namespace": "openbkn-samples", "host": "db", "port": 3306, "database": "supply_demo_hand", "user": "bkn_sample"},
            lambda _args: completed(base64.b64encode(b"secret").decode("ascii")),
        )
        self.assertEqual(config["password"], "secret")



    def test_bundled_deploy_requires_ownership_and_pins_retry_image(self):
        from unittest.mock import patch
        from installer.runtime import deploy
        image = "ghcr.io/openbkn-ai/bkn-samples@sha256:" + "a" * 64
        with patch("installer.runtime.deploy_database", return_value={"image": image}) as called:
            deploy(ROOT, "supply-chain", data_image_ref=image)
        self.assertTrue(called.call_args.kwargs["require_ownership"])
        self.assertEqual(called.call_args.kwargs["data_image_ref"], image)

    def test_resolved_image_allows_retry_with_empty_chart_reference(self):
        from unittest.mock import patch
        from installer.runtime import _record_database_image
        from installer.studio_api import _write_installing, _read_state
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            image = "ghcr.io/openbkn-ai/bkn-samples@sha256:" + "a" * 64
            _write_installing(state, "supply-chain", "0.1.0", data_image_ref=None)
            _record_database_image(state, "supply-chain", "0.1.0", {"image": image})
            current = _read_state(state, "supply-chain")
            self.assertEqual(current["dataImageRef"], image)
            current["status"] = "failed"
            (state / "supply-chain.json").write_text(json.dumps(current))
            def stop_after_deploy(_sample):
                self.assertEqual(_read_state(state, "supply-chain")["dataImageRef"], image)
                raise ControlError("install_failed", "sentinel")
            with patch("installer.runtime.configured_image_ref", return_value=None), self.assertRaises(ApiError) as error:
                retry_sample(sample="supply-chain", installation_id=current["id"], actor_role="admin", state_dir=state,
                             root=ROOT, version="0.1.0", deploy=stop_after_deploy, kubectl=lambda _: None, run=lambda *_: None)
            self.assertEqual(error.exception.code, "install_failed")


if __name__ == "__main__":
    unittest.main()
