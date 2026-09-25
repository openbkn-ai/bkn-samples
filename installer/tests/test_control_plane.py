import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.control_plane import ControlError, create_installation, retry_installation

_INSTALL_PATH = Path(__file__).resolve().parents[2] / "samples/supply_ontology_hand/platform/install_supply.py"
_SPEC = importlib.util.spec_from_file_location("install_supply", _INSTALL_PATH)
_INSTALL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_INSTALL)
build_config = _INSTALL.build_config
commands = _INSTALL.commands

ROOT = Path(__file__).resolve().parents[2]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
NETWORK = {"id": "supply_ontology_hand", "displayName": "供应链本体知识网络-手工版"}
DATABASE = {
    "engine": "mariadb",
    "host": "bkn-sample-supply-chain.openbkn-samples.svc",
    "port": 3306,
    "name": "supply_demo_hand",
    "user": "bkn_sample",
    "password": "secret-value",
}


class OpenBKN:
    def __init__(self, catalogs: list[dict] | None = None, tables: int = 12):
        self.catalogs = list(catalogs or [])
        self.tables = tables
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]):
        self.calls.append(args)
        if args[:3] == ["vega", "catalog", "list"]:
            name = args[args.index("--name") + 1]
            return {"entries": [item for item in self.catalogs if item.get("name") == name]}
        if args[:3] == ["vega", "catalog", "create"]:
            config = json.loads(args[args.index("--connector-config") + 1])
            created = {
                "id": "cat-new",
                "name": args[args.index("--name") + 1],
                "tags": args[args.index("--tags") + 1].split(","),
                "database": config["database"],
            }
            self.catalogs.append(created)
            return created
        if args[:3] == ["vega", "catalog", "resources"]:
            return {"entries": [{"name": f"t{index}"} for index in range(self.tables)]}
        if args[:3] == ["vega", "catalog", "enable"]:
            return {"id": args[3], "enabled": True}
        if args[:3] in (["vega", "catalog", "test-connection"], ["vega", "catalog", "discover"]):
            return {"ok": True}
        raise AssertionError(args)


def hooks(stage: str, payload: dict) -> dict:
    assert "kubectl" not in json.dumps(payload)
    return {
        "ok": True,
        "stage": stage,
        "resources": {
            "catalogId": payload["catalog"]["id"],
            "knowledgeNetworkId": "supply_ontology_hand",
            "capabilitySummary": "declared",
        },
        "checks": [{"name": "tables-discovered", "ok": True}],
    }


class ControlPlaneTest(unittest.TestCase):
    def test_rejects_non_admin(self):
        with self.assertRaises(ControlError) as caught:
            create_installation(
                sample="supply-chain",
                version=VERSION,
                actor_role="member",
                database=DATABASE,
                state_dir=Path(tempfile.mkdtemp()),
                openbkn=OpenBKN(),
                hook_runner=hooks,
                expected_tables=12,
                knowledge_network=NETWORK,
            )
        self.assertEqual(caught.exception.code, "forbidden")

    def test_stops_on_unowned_catalog(self):
        client = OpenBKN([{"id": "cat-old", "name": "bkn-sample-supply-chain", "tags": [], "database": "other"}])
        with self.assertRaises(ControlError) as caught:
            create_installation(
                sample="supply-chain",
                version=VERSION,
                actor_role="admin",
                database=DATABASE,
                state_dir=Path(tempfile.mkdtemp()),
                openbkn=client,
                hook_runner=hooks,
                expected_tables=12,
                knowledge_network=NETWORK,
            )
        self.assertEqual(caught.exception.code, "ownership_conflict")
        self.assertFalse(any(call[:3] == ["vega", "catalog", "create"] for call in client.calls))

    def test_install_then_reject_duplicate(self):
        state = Path(tempfile.mkdtemp())
        client = OpenBKN()
        record = create_installation(
            sample="supply-chain",
            version=VERSION,
            actor_role="admin",
            database=DATABASE,
            state_dir=state,
            openbkn=client,
            hook_runner=hooks,
                expected_tables=12,
                knowledge_network=NETWORK,
        )
        self.assertEqual(record["status"], "installed")
        create_call = next(call for call in client.calls if call[:3] == ["vega", "catalog", "create"])
        self.assertEqual(create_call[create_call.index("--connector-type") + 1], "mysql")
        self.assertIn("secret-value", create_call[create_call.index("--connector-config") + 1])
        self.assertNotIn("secret-value", json.dumps({k: v for k, v in record.items() if k != "resources"}))
        with self.assertRaises(ControlError) as caught:
            create_installation(
                sample="supply-chain",
                version=VERSION,
                actor_role="admin",
                database=DATABASE,
                state_dir=state,
                openbkn=client,
                hook_runner=hooks,
                expected_tables=12,
                knowledge_network=NETWORK,
            )
        self.assertEqual(caught.exception.code, "already_installed")

    def test_retry_after_failed_hook(self):
        state = Path(tempfile.mkdtemp())
        client = OpenBKN()

        def fail_once(stage, payload):
            if stage == "platform-verify":
                return {"ok": False, "message": "smoke failed"}
            return hooks(stage, payload)

        with self.assertRaises(ControlError) as caught:
            create_installation(
                sample="supply-chain",
                version=VERSION,
                actor_role="admin",
                database=DATABASE,
                state_dir=state,
                openbkn=client,
                hook_runner=fail_once,
                expected_tables=12,
                knowledge_network=NETWORK,
            )
        self.assertEqual(caught.exception.code, "verify_failed")
        with self.assertRaises(ControlError) as denied:
            create_installation(
                sample="supply-chain",
                version=VERSION,
                actor_role="admin",
                database=DATABASE,
                state_dir=state,
                openbkn=client,
                hook_runner=hooks,
                expected_tables=12,
                knowledge_network=NETWORK,
            )
        self.assertEqual(denied.exception.code, "use_retry")
        retried = retry_installation(
            sample="supply-chain",
            version=VERSION,
            actor_role="admin",
            database=DATABASE,
            state_dir=state,
            openbkn=client,
            hook_runner=hooks,
            expected_tables=12,
            knowledge_network=NETWORK,
        )
        self.assertEqual(retried["status"], "installed")
        self.assertEqual(retried["capabilitySummary"], "declared")

    def test_changed_capability_summary_is_a_conflict(self):
        state = Path(tempfile.mkdtemp())
        (state / "supply-chain.json").write_text(
            json.dumps(
                {
                    "sample": "supply-chain",
                    "version": VERSION,
                    "status": "failed",
                    "stages": {"knowledge": "succeeded"},
                    "capabilitySummary": "recorded-summary",
                }
            ),
            encoding="utf-8",
        )
        seen = []

        def hook(stage, payload):
            seen.append(payload.get("capabilitySummary"))
            return {
                "ok": False,
                "code": "ownership_conflict",
                "message": "published capabilities do not match the installation record",
            }

        with self.assertRaises(ControlError) as caught:
            retry_installation(
                sample="supply-chain",
                version=VERSION,
                actor_role="admin",
                database=DATABASE,
                state_dir=state,
                openbkn=OpenBKN(),
                hook_runner=hook,
                expected_tables=12,
                knowledge_network=NETWORK,
            )
        self.assertEqual(caught.exception.code, "ownership_conflict")
        self.assertEqual(seen, ["recorded-summary"])
        saved = json.loads((state / "supply-chain.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["capabilitySummary"], "recorded-summary")
        self.assertNotEqual(saved["stages"].get("capabilities"), "succeeded")

    def test_stops_before_the_hook_when_tables_are_missing(self):
        client = OpenBKN(tables=3)
        ran = {"hook": 0}

        def hook(stage, payload):
            ran["hook"] += 1
            return hooks(stage, payload)

        with patch("installer.control_plane.time.sleep"), self.assertRaises(ControlError) as caught:
            create_installation(
                sample="supply-chain",
                version=VERSION,
                actor_role="admin",
                database=DATABASE,
                state_dir=Path(tempfile.mkdtemp()),
                openbkn=client,
                hook_runner=hook,
                expected_tables=12,
                knowledge_network=NETWORK,
            )
        self.assertEqual(caught.exception.code, "discover_incomplete")
        self.assertEqual(ran["hook"], 0)
        self.assertTrue(any(call[:3] == ["vega", "catalog", "enable"] for call in client.calls))


class InstallSupplyTest(unittest.TestCase):
    def test_config_uses_mysql_and_existing_catalog(self):
        payload = {
            "sample": "supply-chain",
            "database": DATABASE,
            "catalog": {"id": "cat-1", "name": "bkn-sample-supply-chain"},
            "knowledgeNetwork": {"id": "supply_ontology_hand", "displayName": "供应链本体知识网络-手工版"},
        }
        config = build_config(payload)
        self.assertEqual(config["database"]["engine"], "mysql")
        self.assertEqual(config["vega"]["catalog_name"], "bkn-sample-supply-chain")
        self.assertEqual(config["vega"]["catalog_id"], "cat-1")
        rendered = json.dumps(commands(Path("config.yaml")))
        self.assertNotIn("kubectl", rendered)
        self.assertIn("import_kn.py", rendered)
        self.assertIn("register_skills.py", rendered)

    def test_supply_hook_stops_before_commands_when_the_summary_differs(self):
        payload = {
            "sample": "supply-chain",
            "components": {"functions": True, "skills": True},
            "database": DATABASE,
            "catalog": {"id": "cat-1", "name": "bkn-sample-supply-chain"},
            "knowledgeNetwork": {"id": "supply_ontology_hand", "displayName": "供应链本体知识网络-手工版"},
            "capabilitySummary": "not-the-sample",
        }
        directory = Path(tempfile.mkdtemp())
        source = directory / "input.json"
        output = directory / "output.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        env = {
            "BKN_SAMPLE_INPUT": str(source),
            "BKN_SAMPLE_OUTPUT": str(output),
            "BKN_SAMPLE_CONFIG": str(directory / "config.yaml"),
        }
        with patch.dict(os.environ, env, clear=False):
            status = _INSTALL.main()
        self.assertEqual(status, 1)
        body = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(body["code"], "ownership_conflict")
        self.assertFalse((directory / "config.yaml").exists())
        self.assertNotIn(DATABASE["password"], output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
