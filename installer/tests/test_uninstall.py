import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock
from urllib.error import HTTPError

from installer.control_plane import ownership_tags
from installer.history import read_installation_history, begin_installation_attempt, record_terminal_installation
from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, _write_installing, _card, installation_view
from installer.uninstall import prepare_uninstall, execute_uninstall, platform_client


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
        self.platform["/api/bkn-backend/v1/knowledge-networks/network-owned/object-metrics/metric-owned"] = {"definition": {"status": "published", "version": 1}}
        self.deleted = []

    def api(self, method, path):
        if method == "GET" and path.startswith("/api/vega-backend/v1/catalogs?"):
            return {"entries": [value for target, value in self.platform.items()
                                if target.startswith("/api/vega-backend/v1/catalogs/")]}
        if method == "GET":
            return self.platform.get(path)
        self.deleted.append(path)
        self.platform.pop(path, None)
        if method == "DELETE" and path == "/api/bkn-backend/v1/knowledge-networks/network-owned":
            for target in list(self.platform):
                if target.startswith(path + "/object-metrics/"):
                    del self.platform[target]

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

    def test_network_delete_cascades_published_metrics_without_legacy_api(self):
        original = self.api
        calls = []
        def checked(method, path):
            calls.append((method, path))
            self.assertNotIn("/metrics", path)
            self.assertNotIn("/object-metrics", path)
            return original(method, path)
        self.api = checked
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstalled")
        self.assertFalse(any("object-metrics" in path for path in self.platform))
        self.assertIn(("DELETE", "/api/bkn-backend/v1/knowledge-networks/network-owned"), calls)
        self.assertIn("/api/agent-operator-integration/v1/skills/other-sample", self.platform)

    def test_delete_conflict_retries_once_then_accepts_empty_success(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b''
        conflict = HTTPError('http://platform/resource', 409, 'Conflict', {}, None)
        with patch.dict('os.environ', {'BKN_BASE_URL': 'http://platform'}), \
             patch('installer.uninstall.urlopen', side_effect=[conflict, response]) as request, \
             patch('installer.uninstall.time.sleep') as sleep:
            self.assertEqual(platform_client('Bearer test')('DELETE', '/resource'), {})
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.kwargs['timeout'], 30)
        sleep.assert_called_once_with(1)

    def test_persistent_delete_conflict_and_permission_errors_remain_failures(self):
        for method, status, attempts in [('DELETE', 409, 2), ('DELETE', 403, 1),
                                         ('DELETE', 401, 1), ('GET', 409, 1)]:
            with self.subTest(method=method, status=status), \
                 patch.dict('os.environ', {'BKN_BASE_URL': 'http://platform'}), \
                 patch('installer.uninstall.urlopen', side_effect=HTTPError('http://platform/resource', status, 'Rejected', {}, None)) as request, \
                 patch('installer.uninstall.time.sleep') as sleep, self.assertRaises(ApiError):
                platform_client('Bearer test')(method, '/resource')
            self.assertEqual(request.call_count, attempts)
            self.assertEqual(sleep.call_count, attempts - 1)

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

    def test_database_read_failure_reports_preflight_and_preserves_all_resources(self):
        original = self.kubectl
        for reason, code in (("Forbidden", "database_permission_denied"),
                             ("Unauthorized", "database_permission_denied"),
                             (None, "database_resource_check_failed")):
            with self.subTest(reason=reason):
                def read(args, body=None):
                    if args[:2] == ["get", "pvc"]:
                        stderr = f"Error from server ({reason}): credential-sentinel" if reason else "connection failed: credential-sentinel"
                        return SimpleNamespace(returncode=1, stdout="", stderr=stderr)
                    return original(args, body)
                self.kubectl = read
                self.start()
                current = _read_state(self.state, "supply-chain")
                self.assertEqual(current["error"]["code"], code)
                self.assertIn("pvc", current["error"]["message"])
                self.assertNotIn("credential-sentinel", json.dumps(current))
                view = installation_view(current, "admin")
                self.assertEqual(view["error"]["stage"], "preflight")
                self.assertEqual(view["stages"][0]["state"], "failed")
                self.assertTrue(all(s["state"] == "pending" for s in view["stages"][1:]))
                self.assertEqual(self.deleted, [])
                self.assertEqual(len(self.database), 4)

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

    def test_registered_sample_outside_legacy_allowlist_can_be_uninstalled(self):
        record = {**self.record, "sample": "supply-chain-en", "id": "inst-supply-chain-en"}
        write_json(self.state / "supply-chain-en.json", record)
        prepare_uninstall(self.state, "supply-chain-en", record["id"], "admin")
        self.assertEqual(_read_state(self.state, "supply-chain-en")["status"], "uninstalling")

    def test_dynamic_sample_card_uses_recorded_receipt(self):
        card = _card({"name": "supply-chain-en"}, "0.1.0",
                     self.record | {"id": "inst-supply-chain-en", "sample": "supply-chain-en"}, "admin", False)
        self.assertTrue(card["canUninstall"])

    def fail_installation(self, **updates):
        self.record.update(status="failed", error={"code": "discover_incomplete", "message": "original scan error"},
                           finishedAt="2026-01-01T00:00:00Z")
        self.record.update(updates)
        write_json(self.state / "supply-chain.json", self.record)

    def test_failed_download_without_resources_can_be_cleaned(self):
        self.fail_installation(resources={}, stages={}, catalogId=None, dataImageRef=None,
                               error={"code": "release_download_failed", "message": "download failed"})
        self.platform.clear()
        self.database.clear()
        original = _read_state(self.state, "supply-chain")
        self.start()
        cleaned = _read_state(self.state, "supply-chain")
        self.assertEqual(cleaned["status"], "uninstalled")
        self.assertEqual(self.deleted, [])
        history, _ = read_installation_history(self.state, "supply-chain", None)
        self.assertIn(original, history)

    def test_legacy_discovery_failure_finds_owned_catalog_without_hook_receipt(self):
        self.fail_installation(resources={}, stages={"database": "succeeded", "discover": "failed"}, catalogId=None)
        self.platform = {"/api/vega-backend/v1/catalogs/catalog-owned": {
            "id": "catalog-owned", "name": "bkn-sample-supply-chain", "tags": ownership_tags("supply-chain", "0.1.3")}}
        self.start()
        cleaned = _read_state(self.state, "supply-chain")
        self.assertEqual(cleaned["status"], "uninstalled")
        self.assertFalse(self.platform)
        self.assertFalse(self.database)
        self.assertEqual(cleaned["catalogId"], "catalog-owned")

    def test_failed_catalog_lookup_is_not_treated_as_no_resources(self):
        self.fail_installation(resources={}, stages={"discover": "failed"}, catalogId=None)
        self.platform.clear()
        original = self.api
        self.api = lambda method, path: None if "catalogs?" in path else original(method, path)
        self.start()
        current = _read_state(self.state, "supply-chain")
        self.assertEqual(current["status"], "uninstall_failed")
        self.assertEqual(self.deleted, [])
        self.assertTrue(self.database)
        self.assertTrue(_card({"name": "supply-chain"}, "0.1.4", current, "admin", False)["canUninstall"])
        self.api = lambda method, path: {"entries": []} if "catalogs?" in path else original(method, path)
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstalled")

    def test_foreign_or_ambiguous_legacy_catalog_blocks_all_deletion(self):
        for ambiguous in (False, True):
            with self.subTest(ambiguous=ambiguous):
                self.fail_installation(resources={}, stages={"discover": "failed"}, catalogId=None)
                entry = {"id": "catalog-owned", "name": "bkn-sample-supply-chain", "tags": []}
                self.platform = {"/api/vega-backend/v1/catalogs/catalog-owned": entry}
                if ambiguous:
                    self.platform["/api/vega-backend/v1/catalogs/catalog-other"] = {**entry, "id": "catalog-other"}
                self.start()
                self.assertEqual(_read_state(self.state, "supply-chain")["error"]["code"], "ownership_conflict")
                self.assertEqual(self.deleted, [])
                self.assertTrue(self.database)

    def test_partial_hook_uses_local_receipts_and_can_resume_cleanup(self):
        self.fail_installation(resources={}, catalogId=None, stages={"knowledge": "failed"})
        shared = self.state / "supply-chain"
        shared.mkdir()
        (shared / "config.yaml").write_text('openbkn:\n  kn_id: network-owned\nvega:\n  catalog_id: catalog-owned\n')
        write_json(shared / "owned-execution.json", {"toolboxes": ["box-owned"], "skills": ["skill-owned"]})
        original_error = self.record["error"]
        original = self.api
        def fail(method, path):
            if method == "DELETE" and path.endswith("skill-owned"):
                raise RuntimeError("cleanup failed")
            return original(method, path)
        self.api = fail
        self.start()
        current = _read_state(self.state, "supply-chain")
        self.assertEqual(current["status"], "uninstall_failed")
        self.assertTrue((shared / "owned-execution.json").exists())
        self.assertTrue(_card({"name": "supply-chain"}, "0.1.4", current, "admin", False)["canUninstall"])
        self.api = original
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["status"], "uninstalled")
        self.assertFalse((shared / "owned-execution.json").exists())
        self.assertFalse(self.database)
        self.assertEqual(list(self.platform), ["/api/agent-operator-integration/v1/skills/other-sample"])
        history, _ = read_installation_history(self.state, "supply-chain", None)
        self.assertTrue(any(item.get("error") == original_error for item in history))

    def test_missing_or_corrupt_partial_hook_receipt_blocks_preparation(self):
        for content in (None, '{', '{"skills": [7], "toolboxes": []}'):
            with self.subTest(content=content):
                self.fail_installation(resources={"knowledgeNetworkId": "network-owned"}, stages={"knowledge": "failed"})
                shared = self.state / "supply-chain"
                shared.mkdir(exist_ok=True)
                if content is not None:
                    (shared / "owned-execution.json").write_text(content)
                with self.assertRaises(ApiError) as caught:
                    prepare_uninstall(self.state, "supply-chain", self.record["id"], "admin")
                self.assertEqual(caught.exception.code, "ownership_receipt_missing")
                self.assertEqual(_read_state(self.state, "supply-chain"), self.record)
                self.assertEqual(self.deleted, [])

    def test_disagreeing_local_configuration_blocks_cleanup(self):
        self.fail_installation(stages={"knowledge": "failed"})
        shared = self.state / "supply-chain"
        shared.mkdir()
        (shared / "config.yaml").write_text('openbkn:\n  kn_id: other-network\nvega:\n  catalog_id: catalog-owned\n')
        with self.assertRaises(ApiError) as caught:
            prepare_uninstall(self.state, "supply-chain", self.record["id"], "admin")
        self.assertEqual(caught.exception.code, "ownership_receipt_missing")
        self.assertEqual(_read_state(self.state, "supply-chain"), self.record)
        self.assertEqual(self.deleted, [])

    def test_cleanup_capability_uses_existing_retry_role(self):
        self.fail_installation(resources={}, stages={})
        for role, allowed in (("admin", True), ("user", False)):
            self.assertEqual(_card({"name": "supply-chain"}, "0.1.4", self.record, role, False)["canUninstall"], allowed)
        with self.assertRaises(ApiError) as caught:
            prepare_uninstall(self.state, "supply-chain", self.record["id"], "user")
        self.assertEqual(caught.exception.status, 403)

    def test_network_only_hook_failure_can_be_cleaned_without_local_receipt_files(self):
        from installer.control_plane import ControlError, create_installation
        from installer.tests.test_control_plane import OpenBKN
        for network_owner in ("absent", "owned", "foreign"):
            with self.subTest(network_owner=network_owner):
                sample, version = "order-basics", "0.1.0"
                initial = {"id": "inst-order-basics", "attemptId": network_owner,
                           "sample": sample, "version": version, "status": "installing",
                           "dataImageRef": "image@sha256:abc", "historyComplete": True,
                           "offlineRelease": {"packageDigest": "fixed"}}
                write_json(self.state / f"{sample}.json", initial)
                def fail_hook(_stage, _payload):
                    return {"ok": False, "message": "knowledge hook failed before writing output"}
                with self.assertRaises(ControlError):
                    create_installation(sample=sample, version=version, actor_role="admin", state_dir=self.state,
                        database={"host": "db", "port": 3306, "name": "order_basics", "user": "sample", "password": "test"},
                        openbkn=OpenBKN(tables=2), hook_runner=fail_hook, expected_tables=2,
                        knowledge_network={"id": "order_basics", "displayName": "Orders"},
                        components={"objects": True, "relations": True, "metrics": False, "functions": False, "skills": False})
                failed = _read_state(self.state, sample)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(failed["stages"]["knowledge"], "failed")
                self.assertEqual(failed["resources"]["ownedExecution"], {"toolboxes": [], "skills": []})
                self.assertTrue(failed["resources"]["knowledgeNetworkPlanned"])
                self.assertFalse((self.state / sample / "config.yaml").exists())
                self.assertFalse((self.state / sample / "owned-execution.json").exists())
                tags = ownership_tags(sample, version)
                network_path = "/api/bkn-backend/v1/knowledge-networks/order_basics"
                unrelated = "/api/agent-operator-integration/v1/skills/other-sample"
                self.platform = {"/api/vega-backend/v1/catalogs/cat-new": {"tags": tags}, unrelated: {}}
                if network_owner != "absent":
                    self.platform[network_path] = {"tags": tags if network_owner == "owned" else []}
                expected_network = self.platform.get(network_path)
                name = "bkn-sample-order-basics"
                annotations = {"openbkn.ai/sample-id": sample, "openbkn.ai/sample-version": version,
                               "openbkn.ai/sample-data-image": initial["dataImageRef"]}
                self.database = {(kind, resource): {"metadata": {"uid": kind, "annotations": annotations}}
                    for kind, resource in (("statefulset", name), ("service", name), ("secret", name), ("pvc", f"data-{name}-0"))}
                self.deleted = []
                prepare_uninstall(self.state, sample, initial["id"], "admin")
                current = _read_state(self.state, sample)
                begin_installation_attempt(self.state, current, failed)
                execute_uninstall(self.state, sample, self.api, self.kubectl)
                self.assertEqual(_read_state(self.state, sample)["status"], "uninstalled")
                self.assertFalse(self.database)
                self.assertIn(unrelated, self.platform)
                if network_owner == "foreign":
                    self.assertEqual(self.platform[network_path], expected_network)
                    self.assertNotIn(network_path, self.deleted)
                else:
                    self.assertNotIn(network_path, self.platform)
                history, _ = read_installation_history(self.state, sample, None)
                self.assertIn(failed, history)

    def test_confirmed_network_ownership_change_still_blocks_all_deletion(self):
        self.fail_installation(stages={"verify": "failed"})
        self.platform["/api/bkn-backend/v1/knowledge-networks/network-owned"]["tags"] = []
        self.start()
        self.assertEqual(_read_state(self.state, "supply-chain")["error"]["code"], "ownership_conflict")
        self.assertEqual(self.deleted, [])
        self.assertTrue(self.database)

    def test_worldcup_network_conflict_before_hook_can_be_cleaned_and_package_removed(self):
        from installer.contract import load_sample
        from installer.control_plane import ControlError, create_installation
        from installer.offline_bundle import OfflinePackages
        from installer.remote_installation import RemoteInstallation
        from installer.tests.test_control_plane import OpenBKN
        root = Path(__file__).resolve().parents[2]
        document = load_sample(root / "samples/world-cup")
        spec = document["spec"]
        sample, version = document["metadata"]["name"], "0.1.2"
        # Cover the publishing branch: only a hook that has not started may skip the receipt.
        components = {**spec["components"], "functions": True}
        initial = {"id": "inst-world-cup", "attemptId": "initial", "sample": sample, "version": version,
                   "status": "installing", "dataImageRef": "image@sha256:abc", "historyComplete": True,
                   "offlineRelease": {"packageDigest": "fixed"}}
        write_json(self.state / f"{sample}.json", initial)
        foreign = {"id": spec["knowledgeNetwork"]["id"], "tags": ["external-owner"]}
        catalog = OpenBKN(tables=spec["database"]["expectedTables"])
        def openbkn(args):
            return foreign if args[:2] == ["bkn", "get"] else catalog(args)
        hook = Mock(side_effect=AssertionError("resource-creating hook must not run"))
        with self.assertRaises(ControlError) as caught:
            create_installation(sample=sample, version=version, actor_role="admin", state_dir=self.state,
                database={"host": "db", "port": 3306, "name": spec["database"]["name"], "user": "sample", "password": "test"},
                openbkn=openbkn, hook_runner=hook, expected_tables=spec["database"]["expectedTables"],
                knowledge_network=spec["knowledgeNetwork"], components=components)
        self.assertEqual(caught.exception.code, "ownership_conflict")
        hook.assert_not_called()
        failed = _read_state(self.state, sample)
        self.assertEqual(failed["resources"]["ownedExecution"], {"toolboxes": [], "skills": []})
        self.assertFalse((self.state / sample / "owned-execution.json").exists())
        runtime = RemoteInstallation(root, self.state, "0.2.0", "arm64", [], "ghcr.io/example/executor@sha256:" + "a" * 64)
        offline = OfflinePackages(root, self.state, runtime)
        cache = offline.directory / sample
        cache.mkdir(parents=True)
        (cache / "package.tar.gz").write_bytes(b"cached-package")
        with self.assertRaises(ApiError):
            offline.delete_package(sample, "admin")
        tags = ownership_tags(sample, version)
        network_path = "/api/bkn-backend/v1/knowledge-networks/" + foreign["id"]
        unrelated = "/api/agent-operator-integration/v1/skills/other-sample"
        self.platform = {network_path: dict(foreign), "/api/vega-backend/v1/catalogs/cat-new": {"tags": tags}, unrelated: {}}
        name = "bkn-sample-world-cup"
        annotations = {"openbkn.ai/sample-id": sample, "openbkn.ai/sample-version": version,
                       "openbkn.ai/sample-data-image": initial["dataImageRef"]}
        self.database = {(kind, resource): {"metadata": {"uid": kind, "annotations": annotations}}
            for kind, resource in (("statefulset", name), ("service", name), ("secret", name), ("pvc", f"data-{name}-0"))}
        self.deleted = []
        prepare_uninstall(self.state, sample, initial["id"], "admin")
        current = _read_state(self.state, sample)
        begin_installation_attempt(self.state, current, failed)
        execute_uninstall(self.state, sample, self.api, self.kubectl)
        self.assertEqual(_read_state(self.state, sample)["status"], "uninstalled")
        self.assertFalse(self.database)
        self.assertEqual(self.platform, {network_path: foreign, unrelated: {}})
        self.assertNotIn(network_path, self.deleted)
        self.assertTrue(offline.delete_package(sample, "admin")["deleted"])
        self.assertFalse(cache.exists())
        history, _ = read_installation_history(self.state, sample, None)
        self.assertIn(failed, history)

    def test_failed_installation_cleanup_then_offline_reinstall_gets_new_identity(self):
        from installer.offline_bundle import OfflinePackages
        from installer.remote_installation import RemoteInstallation
        self.fail_installation(stages={"verify": "failed"}, remoteRelease={"entry": {"version": "0.1.3"}})
        original = _read_state(self.state, "supply-chain")
        self.start()
        cleaned = _read_state(self.state, "supply-chain")
        root = Path(__file__).resolve().parents[2]
        runtime = RemoteInstallation(root, self.state, "0.2.0", "arm64", [], "ghcr.io/example/executor@sha256:" + "a" * 64)
        offline = OfflinePackages(root, self.state, runtime)
        release = {"sample": "supply-chain", "version": "0.1.4", "packageDigest": "sha256:" + "b" * 64,
                   "manifestSha256": "c" * 64, "dataImageRef": "image@sha256:" + "d" * 64,
                   "releaseNotes": {"version": "0.1.4", "documents": []}}
        cache = offline.directory / "supply-chain"
        cache.mkdir(parents=True)
        write_json(cache / "release.json", release)
        offline.prepare(release)
        new = _read_state(self.state, "supply-chain")
        begin_installation_attempt(self.state, new, cleaned)
        self.assertNotEqual(new["id"], original["id"])
        self.assertIn("offlineRelease", new)
        self.assertNotIn("remoteRelease", new)
        with self.assertRaises(ApiError) as caught:
            prepare_uninstall(self.state, "supply-chain", original["id"], "admin")
        self.assertEqual(caught.exception.status, 404)
        history, _ = read_installation_history(self.state, "supply-chain", new)
        self.assertIn(original, history)
