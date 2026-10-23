import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

from installer.deploy_database import (
    GHCR_IMAGE,
    SWR_IMAGE,
    DeployError,
    _pod_state,
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
        self.deleted: list[str] = []

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
        if args[:1] == ["delete"]:
            self.deleted.append(args[2])
            return self._ok("deleted")
        return self._fail(f"unexpected {' '.join(args)}")

    @staticmethod
    def _ok(stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

    @staticmethod
    def _fail(stderr: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class DeployDatabaseTest(unittest.TestCase):
    def setUp(self):
        self._digests = patch("installer.deploy_database.registry_digests", return_value=(DIGEST, DIGEST))
        self.digest_lookup = self._digests.start()

    def tearDown(self):
        self._digests.stop()

    def test_database_ownership_read_failures_are_classified_before_apply(self):
        for reason, code in (("Forbidden", "database_permission_denied"),
                             ("Unauthorized", "database_permission_denied"),
                             (None, "database_resource_check_failed")):
            with self.subTest(reason=reason):
                kubectl = FakeKubectl()
                original = kubectl.__call__
                def read(args, stdin=None):
                    if args[:2] == ["get", "pvc"]:
                        stderr = f"Error from server ({reason}): credential-sentinel" if reason else "connection failed: credential-sentinel"
                        return subprocess.CompletedProcess(args, 1, "", stderr)
                    if "--ignore-not-found" in args:
                        return FakeKubectl._ok("")
                    return original(args, stdin)
                with self.assertRaises(DeployError) as caught:
                    deploy_database(ROOT, "supply-chain", read, require_ownership=True,
                                    data_image_ref=f"{GHCR_IMAGE}@{DIGEST}")
                self.assertEqual(caught.exception.code, code)
                self.assertIn("pvc", caught.exception.message)
                self.assertNotIn("credential-sentinel", caught.exception.message)
                self.assertEqual(kubectl.applied, [])
                self.assertEqual(kubectl.deleted, [])

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
        self.assertIn(f"{SWR_IMAGE}@{DIGEST}", applied)
        self.assertNotIn("kind: Catalog", applied)
        self.assertNotIn("mariadb-root-password: unused", applied)

    def test_reuses_existing_secret(self):
        kubectl = FakeKubectl(secret=True)
        deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.assertNotIn("kind: Secret", kubectl.applied[0])

    def test_pull_failure_never_switches_to_ghcr(self):
        kubectl = FakeKubectl(states=["image_pull_failed", "ready"])
        result = deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _: None,
                                 attempts=3, digests=lambda _: (DIGEST, DIGEST))
        self.assertEqual(kubectl.patched, [])
        self.assertEqual(kubectl.deleted, [])
        self.assertEqual(result["image"], f"{SWR_IMAGE}@{DIGEST}")

    def test_swr_identity_is_independent_of_ghcr_manifest(self):
        kubectl = FakeKubectl()
        result = deploy_database(ROOT, "supply-chain", kubectl,
                                 digests=lambda _: (DIGEST, OTHER))
        self.assertEqual(result["image"], f"{SWR_IMAGE}@{DIGEST}")

    def test_missing_swr_never_automatically_selects_ghcr(self):
        kubectl = FakeKubectl()
        with self.assertRaises(DeployError):
            deploy_database(ROOT, "supply-chain", kubectl, digests=lambda _: (None, DIGEST))
        self.assertEqual(kubectl.applied, [])

    def test_ready_pod_running_another_image_is_still_pending(self):
        def kubectl(args, stdin=None):
            body = {
                "items": [
                    {
                        "spec": {"containers": [{"image": f"{SWR_IMAGE}:0.1.0"}]},
                        "status": {"containerStatuses": [{"ready": True}]},
                    }
                ]
            }
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(body), stderr="")

        self.assertEqual(_pod_state(kubectl, "supply-chain", f"{GHCR_IMAGE}:0.1.0"), "pending")

    def test_explicit_other_registry_reference_is_preserved(self):
        kubectl = FakeKubectl()
        image = f"{GHCR_IMAGE}@{DIGEST}"
        result = deploy_database(ROOT, "supply-chain", kubectl, data_image_ref=image,
                                 digests=lambda _: self.fail("explicit ref must not discover registries"))
        self.assertEqual(result["image"], image)

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

    def test_missing_verified_digest_never_applies_a_mutable_tag(self):
        kubectl = FakeKubectl()
        with self.assertRaises(DeployError) as caught:
            deploy_database(ROOT, "supply-chain", kubectl,
                            digests=lambda _tag: (None, None))
        self.assertEqual(caught.exception.code, "image_unavailable")
        self.assertEqual(kubectl.applied, [])

    def remote_kubectl(self, existing=None, states=None):
        base = FakeKubectl(states=states)
        def invoke(args, stdin=None):
            if "--ignore-not-found" in args:
                resource = (existing or {}).get(args[1])
                return base._ok(json.dumps(resource) if resource else "")
            return base(args, stdin)
        return base, invoke

    def test_remote_deploy_uses_task_image_and_marks_resources_including_pvc(self):
        image = f"{GHCR_IMAGE}@{OTHER}"
        base, kubectl = self.remote_kubectl()
        with patch.dict(os.environ, {"BKN_SAMPLE_DATA_IMAGE_REF": f"{SWR_IMAGE}@{DIGEST}"}):
            result = deploy_database(ROOT, "supply-chain", kubectl, data_image_ref=image, require_ownership=True)
        self.assertEqual(result["image"], image)
        self.digest_lookup.assert_not_called()
        documents = list(yaml.safe_load_all(base.applied[0]))
        for document in documents:
            if document["kind"] != "Namespace":
                self.assertEqual(document["metadata"]["annotations"]["openbkn.ai/sample-data-image"], image)
        sts = next(d for d in documents if d["kind"] == "StatefulSet")
        self.assertEqual(sts["spec"]["volumeClaimTemplates"][0]["metadata"]["annotations"]["openbkn.ai/sample-version"], "0.1.0")

    def test_remote_deploy_rejects_any_unowned_database_resource_before_apply(self):
        for kind in ("statefulset", "service", "secret", "pvc"):
            with self.subTest(kind=kind):
                base, kubectl = self.remote_kubectl({kind: {"metadata": {"name": "existing"}}})
                with self.assertRaises(DeployError) as error:
                    deploy_database(ROOT, "supply-chain", kubectl,
                                    data_image_ref=f"{GHCR_IMAGE}@{DIGEST}", require_ownership=True)
                self.assertEqual(error.exception.code, "ownership_conflict")
                self.assertEqual(base.applied, [])
                self.assertEqual(base.deleted, [])

    def test_remote_failed_first_boot_keeps_the_database_volume(self):
        base, kubectl = self.remote_kubectl(states=["sample_data_unavailable"])
        with self.assertRaises(DeployError) as error:
            deploy_database(ROOT, "world-cup", kubectl, data_image_ref=f"{GHCR_IMAGE}@{DIGEST}",
                            require_ownership=True, attempts=1)
        self.assertEqual(error.exception.code, "sample_data_unavailable")
        self.assertEqual(base.deleted, [])

    def test_uses_the_published_main_build_tag(self):
        kubectl = FakeKubectl()
        tag = "0.1.0-main.20260925021424.sha912ed7b"
        with patch.dict(os.environ, {"BKN_SAMPLE_DATA_IMAGE_TAG": tag}):
            result = deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.digest_lookup.assert_called_once_with(tag)
        self.assertIn(f"{SWR_IMAGE}@{DIGEST}", kubectl.applied[0])
        self.assertEqual(result["image"], f"{SWR_IMAGE}@{DIGEST}")

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
        self.assertEqual(kubectl.deleted, ["bkn-sample-world-cup-0", "data-bkn-sample-world-cup-0"])

    def test_waits_between_checks_instead_of_spinning(self):
        kubectl = FakeKubectl(states=["pending", "pending", "ready"])
        waits = []
        deploy_database(ROOT, "supply-chain", kubectl, sleep=waits.append, attempts=5, poll_seconds=7,
                        digests=lambda _tag: (DIGEST, DIGEST))
        self.assertEqual(waits, [7, 7])

    def test_reports_database_not_ready(self):
        kubectl = FakeKubectl(states=["pending"])
        with self.assertRaises(DeployError) as caught:
            deploy_database(ROOT, "supply-chain", kubectl, sleep=lambda _seconds: None, attempts=1)
        self.assertEqual(caught.exception.code, "database_not_ready")


    def test_bundled_default_reference_has_ownership_annotations(self):
        base, kubectl = self.remote_kubectl()
        with patch.dict(os.environ, {}, clear=True):
            result = deploy_database(ROOT, "supply-chain", kubectl, digests=lambda _: (DIGEST, None), require_ownership=True)
        documents = [d for d in yaml.safe_load_all(base.applied[0]) if d.get("kind") != "Namespace"]
        self.assertEqual(len(documents), 3)
        for document in documents:
            self.assertEqual(document["metadata"]["annotations"]["openbkn.ai/sample-data-image"], result["image"])
        claim = next(d for d in documents if d["kind"] == "StatefulSet")["spec"]["volumeClaimTemplates"][0]
        self.assertEqual(claim["metadata"]["annotations"]["openbkn.ai/sample-data-image"], result["image"])

    def test_owned_database_does_not_drift_from_its_image_annotations(self):
        base, kubectl = self.remote_kubectl(states=["image_pull_failed"])
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(DeployError) as error:
            deploy_database(ROOT, "supply-chain", kubectl, digests=lambda _: (DIGEST, DIGEST),
                            require_ownership=True, attempts=1)
        self.assertEqual(error.exception.code, "image_unavailable")
        self.assertFalse(base.patched)


class PollingTest(unittest.TestCase):
    def test_waits_between_checks_instead_of_spinning(self):
        waits = []
        kubectl = FakeKubectl(states=["pending", "pending", "ready"])
        deploy_database(ROOT, "supply-chain", kubectl, sleep=waits.append, attempts=5, poll_seconds=7,
                        digests=lambda _tag: (DIGEST, DIGEST))
        self.assertEqual(waits, [7, 7])





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
        self.assertEqual((swr, ghcr), (DIGEST, None))
        self.assertEqual(len(seen), 1)
        self.assertIn('myhuaweicloud.com', seen[0].full_url)
        self.assertEqual(seen[0].get_method(), 'HEAD')

    def test_missing_manifest_is_empty(self):
        def opener(_request, timeout=10):
            raise OSError("missing")

        self.assertEqual(registry_digests("0.1.0", opener), (None, None))


if __name__ == "__main__":
    unittest.main()
