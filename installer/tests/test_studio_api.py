import json
import tempfile
import unittest
from pathlib import Path

from installer.contract import OFFICIAL_SOURCE_REPO
from installer.studio_api import (
    ApiError,
    create_sample_installation,
    get_sample_installation,
    list_samples,
    retry_sample_installation,
)

DIGEST = "a" * 64


def index(name: str = "supply-chain", digest: str = DIGEST) -> dict:
    return {
        "sourceRepo": OFFICIAL_SOURCE_REPO,
        "version": "0.1.0",
        "samples": [
            {
                "name": name,
                "displayName": "Supply",
                "summary": "Orders and stock.",
                "licenseNote": "Demo",
                "questions": ["Can this order ship?"],
                "expectedTables": 12,
                "knowledgeNetworkId": "supply_ontology_hand",
                "knowledgeNetworkDisplayName": "Supply network",
                "manifestSha256": digest,
            }
        ],
    }


class StudioApiTest(unittest.TestCase):
    def test_catalog_comes_from_the_index_and_hides_install_for_users(self):
        catalog = list_samples(
            pinned_version="0.1.0",
            image_index=index(),
            repo_index=index(),
            state_dir=Path(tempfile.mkdtemp()),
            actor_role="user",
        )
        sample = catalog["samples"][0]
        self.assertEqual(sample["name"], "supply-chain")
        self.assertEqual(sample["status"], "not_installed")
        self.assertFalse(sample["installable"])
        self.assertEqual(sample["questions"], [])

    def test_sha_mismatch_is_not_installable(self):
        catalog = list_samples(
            pinned_version="0.1.0",
            image_index=index(digest="b" * 64),
            repo_index=index(),
            state_dir=Path(tempfile.mkdtemp()),
            actor_role="admin",
        )
        sample = catalog["samples"][0]
        self.assertEqual(sample["status"], "unavailable")
        self.assertFalse(sample["installable"])

    def test_install_retry_and_conflict_follow_the_control_plane(self):
        state = Path(tempfile.mkdtemp())
        database = {"name": "supply_demo_hand", "host": "db", "port": 3306, "user": "bkn_sample", "password": "secret"}
        calls = {"deploy": 0}

        def deploy(_sample):
            calls["deploy"] += 1

        def openbkn(args):
            if "list" in args:
                return {"entries": []}
            return {"id": "cat-1", "name": "bkn-sample-supply-chain"}

        def hook(_stage, _payload):
            return {"ok": True, "resources": {"knowledgeNetworkId": "supply_ontology_hand"}}

        created = create_sample_installation(
            sample="supply-chain",
            actor_role="admin",
            state_dir=state,
            version="0.1.0",
            database=database,
            openbkn=openbkn,
            hook_runner=hook,
            deploy=deploy,
        )
        self.assertEqual(created["status"], "installed")
        self.assertEqual(calls["deploy"], 1)
        self.assertNotIn("secret", json.dumps(created))
        loaded = get_sample_installation(
            sample="supply-chain",
            installation_id=created["id"],
            state_dir=state,
            actor_role="user",
        )
        self.assertEqual(loaded["id"], created["id"])

        again = list_samples(
            pinned_version="0.1.0",
            image_index=index(),
            repo_index=index(),
            state_dir=state,
            actor_role="admin",
        )
        self.assertEqual(again["samples"][0]["status"], "installed")
        self.assertFalse(again["samples"][0]["installable"])
        self.assertEqual(again["samples"][0]["questions"], ["Can this order ship?"])
        with self.assertRaises(ApiError) as caught:
            create_sample_installation(
                sample="supply-chain",
                actor_role="admin",
                state_dir=state,
                version="0.1.0",
                database=database,
                openbkn=openbkn,
                hook_runner=hook,
                deploy=deploy,
            )
        self.assertEqual(caught.exception.code, "already_installed")
        self.assertEqual(caught.exception.status, 409)

    def test_non_admin_cannot_install(self):
        calls = {"deploy": 0}

        def deploy(_sample):
            calls["deploy"] += 1

        with self.assertRaises(ApiError) as caught:
            create_sample_installation(
                sample="supply-chain",
                actor_role="user",
                state_dir=Path(tempfile.mkdtemp()),
                version="0.1.0",
                database={"name": "supply_demo_hand"},
                openbkn=lambda _args: {"entries": []},
                hook_runner=lambda *_args: {"ok": True},
                deploy=deploy,
            )
        self.assertEqual(caught.exception.code, "forbidden")
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(calls["deploy"], 0)

    def test_retry_uses_the_existing_installation_id(self):
        state = Path(tempfile.mkdtemp())
        (state / "supply-chain.json").write_text(
            json.dumps(
                {
                    "id": "inst-supply-chain",
                    "sample": "supply-chain",
                    "version": "0.1.0",
                    "status": "failed",
                    "stages": {"discover": "succeeded"},
                    "error": {"code": "verify_failed", "message": "smoke failed"},
                }
            ),
            encoding="utf-8",
        )

        def openbkn(args):
            if "list" in args:
                return {"entries": [{"id": "cat-1", "name": "bkn-sample-supply-chain", "tags": ["bkn-samples", "bkn-sample:supply-chain", "bkn-samples-version:0.1.0"]}]}
            return {"id": "cat-1"}

        retried = retry_sample_installation(
            sample="supply-chain",
            installation_id="inst-supply-chain",
            actor_role="admin",
            state_dir=state,
            version="0.1.0",
            database={"name": "supply_demo_hand"},
            openbkn=openbkn,
            hook_runner=lambda *_args: {"ok": True, "resources": {}},
            deploy=lambda _sample: None,
        )
        self.assertEqual(retried["status"], "installed")
        self.assertEqual(retried["id"], "inst-supply-chain")


if __name__ == "__main__":
    unittest.main()
