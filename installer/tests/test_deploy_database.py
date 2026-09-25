import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from installer.deploy_database import (
    GHCR_IMAGE,
    SWR_IMAGE,
    DeployError,
    deploy_database,
    registry_digests,
)

DIGEST = "sha256:" + "ab" * 32
OTHER = "sha256:" + "cd" * 32

ROOT = Path(__file__).resolve().parents[2]


class FakeKubectl:
    def __init__(self, storage: bool = True, secret: bool = False, states: list[str] | None = None):
        self.storage = storage
        self.secret = secret
        self.states = list(states or ["ready"])
        self.applied: list[str] = []
        self.patched: list[str] = []

    def __call__(self, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
        if args[:2] == ["get", "storageclass"]:
            items = []
            if self.storage:
                items.append(
                    {
                        "metadata": {
                            "name": "standard",
                            "annotations": {"storageclass.kubernetes.io/is-default-class": "true"},
                        }
                    }
                )
            return self._ok(json.dumps({"items": items}))
        if args[:2] == ["get", "secret"]:
            return self._ok("secret/bkn-sample-supply-chain") if self.secret else self._fail("not found")
        if args[:2] == ["apply", "-f"]:
            self.applied.append(stdin or "")
            return self._ok("applied")
        if args[:2] == ["get", "pods"]:
            state = self.states.pop(0) if self.states else "pending"
            if state == "ready":
                status = {"containerStatuses": [{"ready": True}]}
            elif state == "image_pull_failed":
                status = {"containerStatuses": [{"ready": False, "state": {"waiting": {"reason": "ImagePullBackOff"}}}]}
            elif state == "sample_data_unavailable":
                status = {
                    "containerStatuses": [
                        {
                            "ready": False,
                            "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                            "lastState": {"terminated": {"exitCode": 1}},
                        }
                    ]
                }
            else:
                status = {"containerStatuses": [{"ready": False, "state": {"waiting": {"reason": "PodInitializing"}}}]}
            return self._ok(json.dumps({"items": [{"status": status}]}))
        if args[:1] == ["logs"]:
            return self._ok("sample data unavailable: matches.csv")
        if args[:1] == ["patch"]:
            self.patched.append(args[-1])
            return self._ok("patched")
        return self._fail(f"unexpected {' '.join(args)}")

    @staticmethod
    def _ok(stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

    @staticmethod
    def _fail(stderr: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class DeployDatabaseTest(unittest.TestCase):
    def test_missing_storage_class_creates_nothing(self):
        kubectl = FakeKubectl(storage=False)
        with self.assertRaises(DeployError) as caught:
            deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.assertEqual(caught.exception.code, "storage_class_missing")
        self.assertEqual(kubectl.applied, [])

    def test_creates_database_without_printing_password(self):
        kubectl = FakeKubectl()
        result = deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.assertEqual(result["host"], "bkn-sample-supply-chain.openbkn-samples.svc")
        self.assertEqual(result["database"], "supply_demo_hand")
        self.assertNotIn("password", result)
        applied = kubectl.applied[0]
        self.assertIn("kind: Secret", applied)
        self.assertIn(f"{SWR_IMAGE}:0.1.0", applied)
        self.assertNotIn("kind: Catalog", applied)
        self.assertNotIn("mariadb-root-password: unused", applied)

    def test_reuses_existing_secret(self):
        kubectl = FakeKubectl(secret=True)
        deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.assertNotIn("kind: Secret", kubectl.applied[0])

    def test_switches_to_ghcr_when_manifest_digests_match(self):
        kubectl = FakeKubectl(states=["image_pull_failed", "ready"])
        result = deploy_database(
            ROOT,
            "supply-chain",
            kubectl,
            sleep=lambda _seconds: None,
            attempts=3,
            digests=lambda _tag: (DIGEST, DIGEST),
        )
        self.assertIn(f"{GHCR_IMAGE}:0.1.0", kubectl.patched[0])
        self.assertEqual(result["image"], f"{GHCR_IMAGE}:0.1.0")

    def test_refuses_ghcr_when_manifest_digests_differ(self):
        kubectl = FakeKubectl(states=["image_pull_failed", "ready"])
        with self.assertRaises(DeployError) as caught:
            deploy_database(
                ROOT,
                "supply-chain",
                kubectl,
                sleep=lambda _seconds: None,
                attempts=3,
                digests=lambda _tag: (DIGEST, OTHER),
            )
        self.assertEqual(caught.exception.code, "image_unavailable")
        self.assertEqual(kubectl.patched, [])
        self.assertIn("digests differ", caught.exception.message)

    def test_switches_to_ghcr_when_swr_has_no_manifest(self):
        kubectl = FakeKubectl(states=["image_pull_failed", "ready"])
        result = deploy_database(
            ROOT,
            "supply-chain",
            kubectl,
            sleep=lambda _seconds: None,
            attempts=3,
            digests=lambda _tag: (None, DIGEST),
        )
        self.assertEqual(result["image"], f"{GHCR_IMAGE}:0.1.0")

    def test_reports_image_unavailable_when_both_registries_fail(self):
        kubectl = FakeKubectl(states=["image_pull_failed", "image_pull_failed"])
        with self.assertRaises(DeployError) as caught:
            deploy_database(
                ROOT,
                "supply-chain",
                kubectl,
                sleep=lambda _seconds: None,
                attempts=2,
                digests=lambda _tag: (DIGEST, DIGEST),
            )
        self.assertEqual(caught.exception.code, "image_unavailable")

    def test_uses_the_published_main_build_tag(self):
        kubectl = FakeKubectl()
        tag = "0.1.0-main.20260925021424.sha912ed7b"
        with patch.dict(os.environ, {"BKN_SAMPLE_DATA_IMAGE_TAG": tag}):
            result = deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.assertIn(f"{SWR_IMAGE}:{tag}", kubectl.applied[0])
        self.assertEqual(result["image"], f"{SWR_IMAGE}:{tag}")

    def test_rejects_latest_image_tag(self):
        with patch.dict(os.environ, {"BKN_SAMPLE_DATA_IMAGE_TAG": "latest"}):
            with self.assertRaises(DeployError) as caught:
                deploy_database(ROOT, "supply-chain", FakeKubectl(), sleep=lambda _seconds: None, attempts=1)
        self.assertEqual(caught.exception.code, "image_unavailable")

    def test_download_failure_does_not_wait_for_a_catalog(self):
        kubectl = FakeKubectl(states=["sample_data_unavailable"])
        with self.assertRaises(DeployError) as caught:
            deploy_database(ROOT, "world-cup", kubectl, sleep=lambda _seconds: None, attempts=5)
        self.assertEqual(caught.exception.code, "sample_data_unavailable")
        self.assertEqual(len(kubectl.applied), 1)

    def test_reports_database_not_ready(self):
        kubectl = FakeKubectl(states=["pending"])
        with self.assertRaises(DeployError) as caught:
            deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.assertEqual(caught.exception.code, "database_not_ready")


class _Response:
    def __init__(self, headers: dict | None = None, body: bytes = b""):
        self.headers = headers or {}
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class RegistryDigestTest(unittest.TestCase):
    def test_reads_the_manifest_list_digest(self):
        seen = []

        def opener(request, timeout=10):
            seen.append(request)
            if request.full_url.startswith("https://ghcr.io/token"):
                return _Response(body=b'{"token":"pull-token"}')
            return _Response({"Docker-Content-Digest": DIGEST})

        swr, ghcr = registry_digests("0.1.0", opener)
        self.assertEqual((swr, ghcr), (DIGEST, DIGEST))
        ghcr_request = next(item for item in seen if item.full_url.startswith("https://ghcr.io/v2/"))
        self.assertEqual(ghcr_request.get_method(), "HEAD")
        self.assertEqual(ghcr_request.get_header("Authorization"), "Bearer pull-token")

    def test_missing_manifest_is_empty(self):
        def opener(_request, timeout=10):
            raise OSError("missing")

        self.assertEqual(registry_digests("0.1.0", opener), (None, None))


if __name__ == "__main__":
    unittest.main()
