import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from installer.control_plane import ownership_tags
from installer.history import read_installation_history, begin_installation_attempt, record_terminal_installation
from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, _write_installing, _card
from installer.uninstall import prepare_uninstall, execute_uninstall


class UninstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)
        self.record = {"id": "inst-supply-chain", "attemptId": "old", "sample": "supply-chain", "version": "0.1.3",
                       "status": "installed", "historyComplete": True, "catalogId": "catalog-owned", "dataImageRef": "image@sha256:abc",
                       "resources": {"knowledgeNetworkId": "network-owned", "ownedExecution": {"toolboxes": ["box-owned"], "skills": ["skill-owned"]}}}
        write_json(self.state / "supply-chain.json", self.record)
        tags = ownership_tags("supply-chain", "0.1.3")
        self.platform = {"/api/bkn-backend/v1/knowledge-networks/network-owned": {"tags": tags},
                         "/api/vega-backend/v1/catalogs/catalog-owned": {"tags": tags},
                         "/api/agent-operator-integration/v1/tool-box/box-owned": {},
                         "/api/agent-operator-integration/v1/skills/skill-owned": {},
                         "/api/agent-operator-integration/v1/skills/other-sample": {}}
        annotations = {"openbkn.ai/sample-id": "supply-chain", "openbkn.ai/sample-version": "0.1.3", "openbkn.ai/sample-data-image": "image@sha256:abc"}
        self.database = {(kind, name): {"metadata": {"uid": kind, "annotations": annotations}} for kind, name in
                         [("statefulset", "bkn-sample-supply-chain"), ("service", "bkn-sample-supply-chain"), ("secret", "bkn-sample-supply-chain"), ("pvc", "data-bkn-sample-supply-chain-0")]}
        self.platform["/api/bkn-backend/v1/knowledge-networks/network-owned/metrics/metric-owned"] = {}
        self.deleted = []

    def api(self, method, path):
        if method == "GET" and "/metrics?" in path:
            return {"entries": [{"id": "metric-owned"}]} if path.split("/metrics?")[0] + "/metrics/metric-owned" in self.platform else {"entries": []}
        if method == "GET":
            return self.platform.get(path)
        self.deleted.append(path)
        self.platform.pop(path, None)

    def kubectl(self, args, body=None):
        if args[0] == "get":
            value = self.database.get((args[1], args[2]))
            return SimpleNamespace(returncode=0, stdout=json.dumps(value) if value else "")
        self.assertEqual(args[:2], ["delete", "--raw"])
        plural = args[2].split("/")[-2]
        kind = {"statefulsets": "statefulset", "services": "service", "secrets": "secret", "persistentvolumeclaims": "pvc"}[plural]
        self.assertEqual(json.loads(body)["preconditions"]["uid"], kind)
        del self.database[(kind, args[2].split("/")[-1])]
        return SimpleNamespace(returncode=0)

    def start(self):
        previous = _read_state(self.state, "supply-chain")
        prepare_uninstall(self.state, "supply-chain", "inst-supply-chain", "admin")
        current = _read_state(self.state, "supply-chain")
        begin_installation_attempt(self.state, current, previous)
        execute_uninstall(self.state, "supply-chain", self.api, self.kubectl)

    def test_uninstall_then_reinstall_preserves_history_and_unrelated_resources(self):
        self.start()
        current = _read_state(self.state, "supply-chain")
        self.assertEqual(current["status"], "uninstalled")
        self.assertFalse(self.database)
        self.assertEqual(list(self.platform), ["/api/agent-operator-integration/v1/skills/other-sample"])
        card = _card({"name": "supply-chain"}, "0.1.4", current, "admin", False)
        self.assertEqual(card["status"], "not_installed")
        self.assertTrue(card["installable"])
        _write_installing(self.state, "supply-chain", "0.1.4")
        new = _read_state(self.state, "supply-chain")
        begin_installation_attempt(self.state, new, current)
        new.update(status="installed", finishedAt="2099-01-01T00:00:00Z")
        record_terminal_installation(self.state, new)
        history, complete = read_installation_history(self.state, "supply-chain", new)
        self.assertEqual({(r["version"], r["status"]) for r in history}, {("0.1.3", "installed"), ("0.1.3", "uninstalled"), ("0.1.4", "installed")})
        self.assertEqual(len(history), 3)
        self.assertNotEqual(new["id"], current["id"])
        self.assertTrue(complete)
        with self.assertRaises(ApiError):
            prepare_uninstall(self.state, "supply-chain", current["id"], "admin")

    def test_unowned_database_blocks_all_deletion(self):
        self.database[("service", "bkn-sample-supply-chain")]["metadata"]["annotations"] = {}
        self.start()
        self.assertEqual(self.deleted, [])
        self.assertEqual(_read_state(self.state, "supply-chain")["error"]["code"], "ownership_conflict")

    def test_published_execution_resources_are_taken_offline_before_delete(self):
        original = self.api
        calls = []
        for path in self.platform:
            if path.endswith(("skill-owned", "box-owned")):
                self.platform[path]["status"] = "published"
        def lifecycle(method, path, body=None):
            calls.append((method, path))
            if path.endswith("/status"):
                self.assertEqual(body, {"status": "offline"})
                self.assertEqual(method, "PUT" if "/skills/" in path else "POST")
                self.platform[path[:-7]]["status"] = "offline"
                return {}
            if method == "DELETE" and path in self.platform:
                self.assertNotEqual(self.platform[path].get("status"), "published")
            return original(method, path)
        self.api = lifecycle
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstalled")
        for path in ("/api/agent-operator-integration/v1/skills/skill-owned", "/api/agent-operator-integration/v1/tool-box/box-owned"):
            down = "PUT" if "/skills/" in path else "POST"
            self.assertLess(calls.index((down, path + "/status")), calls.index(("DELETE", path)))

    def test_downline_failure_keeps_execution_resources_for_retry(self):
        original = self.api
        path = "/api/agent-operator-integration/v1/skills/skill-owned"
        self.platform[path]["status"] = "published"
        def fail(method, target, body=None):
            if target.endswith("/status"):
                raise RuntimeError("downline failed")
            return original(method, target)
        self.api = fail
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstall_failed")
        self.assertIn(path, self.platform)
        self.assertTrue(self.database)

    def test_missing_receipt_and_non_admin_are_rejected(self):
        self.record["resources"].pop("ownedExecution")
        write_json(self.state / "supply-chain.json", self.record)
        for role, status in [("user", 403), ("admin", 409)]:
            with self.assertRaises(ApiError) as caught:
                prepare_uninstall(self.state, "supply-chain", "inst-supply-chain", role)
            self.assertEqual(caught.exception.status, status)

    def test_partial_failure_can_resume_without_losing_install_history(self):
        original = self.api
        def fail(method, path):
            if method == "DELETE" and path.endswith("skill-owned"):
                raise RuntimeError("failed")
            return original(method, path)
        self.api = fail
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstall_failed")
        self.api = original
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstalled")
        history, _ = read_installation_history(self.state, "supply-chain", None)
        self.assertEqual(len(history), 3)


    def test_enveloped_resources_and_offline_catalog_still_allow_uninstall(self):
        for path in ("/api/bkn-backend/v1/knowledge-networks/network-owned", "/api/vega-backend/v1/catalogs/catalog-owned"):
            self.platform[path] = {"entries": [self.platform[path]]}
        card = _card({"name": "supply-chain", "status": "unavailable"}, "0.1.3", self.record, "admin", True)
        self.assertTrue(card["canUninstall"])
        self.assertEqual(card["status"], "installed")
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstalled")


    def test_restart_marks_uninstall_failed_and_preserves_operation(self):
        from installer.task_runner import InstallationRunner
        prepare_uninstall(self.state, "supply-chain", self.record["id"], "admin")
        InstallationRunner(self.state, ["supply-chain"]).recover_interrupted()
        current = _read_state(self.state, "supply-chain")
        self.assertEqual(current["status"], "uninstall_failed")
        self.assertEqual(current["error"]["code"], "uninstall_interrupted")
        self.assertEqual(current["operation"], "uninstall")

    def test_empty_execution_receipt_is_valid_for_order_basics(self):
        record = {**self.record, "sample": "order-basics", "id": "inst-order-basics", "resources": {"ownedExecution": {"skills": [], "toolboxes": []}}}
        write_json(self.state / "order-basics.json", record)
        prepare_uninstall(self.state, "order-basics", record["id"], "admin")
        self.assertEqual(_read_state(self.state, "order-basics")["status"], "uninstalling")
