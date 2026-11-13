import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml

from installer import workshop_apps
from installer.control_plane import ControlError, create_installation, ownership_tags, retry_installation
from installer.history import begin_installation_attempt
from installer.state_store import write_json
from installer.studio_api import _read_state
from installer.tests.test_control_plane import DATABASE, NETWORK, VERSION, OpenBKN, hooks
from installer.uninstall import execute_uninstall, prepare_uninstall
from tools.publication.build_candidate import included

APPS = "/api/workshop/v1/apps"


def spec(name="Kit schedule", network="supply_ontology_hand"):
    return {"apiVersion": "workshop.openbkn.ai/v1", "app": {"id": "app-exported", "name": name, "description": "Plans"},
            "dependencies": {"knowledgeNetwork": {"id": network, "name": "exported name"}},
            "sources": [], "variables": [], "pages": [{"id": "plan", "title": "Plan"}], "theme": {}}


class Workshop:
    """Workshop's app API: list by network and name (substring), create, publish, get, delete."""

    def __init__(self, apps=None):
        self.apps = {app["id"]: app for app in (apps or [])}
        self.calls = []
        self.count = 0

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and path.startswith(APPS + "?"):
            query = dict(part.split("=", 1) for part in path.split("?", 1)[1].split("&"))
            from urllib.parse import unquote
            entries = [{k: v for k, v in app.items() if k != "draft"} for app in self.apps.values()
                       if app["kn"]["id"] == unquote(query["kn_id"]) and unquote(query["name"]) in app["name"]]
            return {"entries": entries, "next_cursor": ""}
        if method == "POST" and path == APPS:
            self.count += 1
            app = {"id": f"app-{self.count}", "name": body["name"], "kn": body["kn"], "draft": body["draft"],
                   "draft_revision": 1, "status": "draft", "current_version": 0}
            self.apps[app["id"]] = app
            return app
        app_id = path[len(APPS) + 1:].split("/")[0]
        if method == "POST" and path.endswith("/publish"):
            self.apps[app_id].update(status="published", current_version=1, published=body)
            return {"app_id": app_id, "version": 1}
        if method == "GET":
            return self.apps.get(app_id)
        if method == "DELETE":
            self.apps.pop(app_id, None)
            return {}
        raise AssertionError((method, path))


class AppSpecTest(unittest.TestCase):
    def test_an_exported_spec_must_belong_to_the_sample_network(self):
        self.assertEqual(workshop_apps.validate(spec(), "supply_ontology_hand"), [])
        self.assertTrue(workshop_apps.validate(spec(network="other"), "supply_ontology_hand"))
        self.assertTrue(workshop_apps.validate({**spec(), "apiVersion": "v0"}, "supply_ontology_hand"))
        self.assertTrue(workshop_apps.validate({**spec(), "pages": []}, "supply_ontology_hand"))
        self.assertTrue(workshop_apps.validate({**spec(), "app": {"id": "x"}}, "supply_ontology_hand"))

    def test_samples_load_apps_from_their_workshop_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "workshop" / "apps"
            folder.mkdir(parents=True)
            (folder / "kit.app.yaml").write_text(yaml.safe_dump(spec(), allow_unicode=True), encoding="utf-8")
            (folder / "notes.txt").write_text("not an app", encoding="utf-8")
            self.assertEqual([s["app"]["name"] for s in workshop_apps.specs(Path(tmp), "supply_ontology_hand")], ["Kit schedule"])
            (folder / "twin.app.yaml").write_text(yaml.safe_dump(spec()), encoding="utf-8")
            with self.assertRaises(workshop_apps.AppError):
                workshop_apps.specs(Path(tmp), "supply_ontology_hand")

    def test_packages_carry_the_workshop_folder(self):
        self.assertTrue(included(Path("workshop/apps/kit.app.yaml")))


class InstallAppsTest(unittest.TestCase):
    network = {"id": "supply_ontology_hand", "name": "供应链"}

    def test_creates_and_publishes_each_app_on_the_sample_network(self):
        platform, remembered = Workshop(), []
        created = workshop_apps.install(platform, [spec()], self.network, [], remembered.append)
        self.assertEqual(created, [{"id": "app-1", "name": "Kit schedule"}])
        app = platform.apps["app-1"]
        self.assertEqual(app["kn"], self.network)
        self.assertEqual(app["draft"]["dependencies"]["knowledgeNetwork"], self.network)
        self.assertEqual((app["status"], app["published"]["revision"]), ("published", 1))
        self.assertEqual(remembered[-1], created)

    def test_installing_again_replaces_recorded_and_same_name_apps_only(self):
        other_network = {"id": "app-other", "name": "Kit schedule", "kn": {"id": "another", "name": "x"}}
        renamed = {"id": "app-mine", "name": "Kit schedule (copy)", "kn": dict(self.network)}
        stale = {"id": "app-stale", "name": "Kit schedule", "kn": dict(self.network)}
        recorded = {"id": "app-recorded", "name": "Old name", "kn": dict(self.network)}
        platform = Workshop([other_network, renamed, stale, recorded])
        created = workshop_apps.install(platform, [spec()], self.network, [{"id": "app-recorded", "name": "Old name"}])
        self.assertEqual(set(platform.apps), {"app-other", "app-mine", created[0]["id"]})

    def test_an_app_already_removed_is_not_an_error(self):
        platform = Workshop()
        workshop_apps.install(platform, [spec()], self.network, [{"id": "gone", "name": "Kit schedule"}])
        self.assertNotIn(("DELETE", f"{APPS}/gone", None), platform.calls)


class InstallationRecordTest(unittest.TestCase):
    def install(self, state, step, create=True):
        call = create_installation if create else retry_installation
        return call(sample="supply-chain", version=VERSION, actor_role="admin", database=DATABASE, state_dir=state,
                    openbkn=OpenBKN(), hook_runner=hooks, expected_tables=12, knowledge_network=NETWORK,
                    workshop_apps=step)

    def test_apps_are_created_after_verification_and_recorded(self):
        state, seen = Path(tempfile.mkdtemp()), []

        def step(recorded, remember):
            seen.append((recorded, _read_state(state, "supply-chain")["stages"].get("verify")))
            remember([{"id": "app-1", "name": "Kit schedule"}])
        record = self.install(state, step)
        self.assertEqual(seen, [([], "running")])
        self.assertEqual(record["status"], "installed")
        self.assertEqual(_read_state(state, "supply-chain")["workshopApps"], [{"id": "app-1", "name": "Kit schedule"}])

    def test_a_failed_app_step_fails_the_installation_and_retry_gets_the_receipt(self):
        state, seen = Path(tempfile.mkdtemp()), []

        def failing(recorded, remember):
            remember([{"id": "app-1", "name": "Kit schedule"}])
            raise ControlError("workshop_unavailable", "Workshop did not accept the sample's apps")
        with self.assertRaises(ControlError):
            self.install(state, failing)
        failed = _read_state(state, "supply-chain")
        self.assertEqual((failed["status"], failed["stages"]["verify"]), ("failed", "failed"))
        self.assertEqual(failed["workshopApps"], [{"id": "app-1", "name": "Kit schedule"}])
        record = self.install(state, lambda recorded, remember: seen.append(recorded), create=False)
        self.assertEqual(record["status"], "installed")
        self.assertEqual(seen, [[{"id": "app-1", "name": "Kit schedule"}]])


class UninstallAppsTest(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        tags = ownership_tags("supply-chain", "0.1.3")
        self.platform = {"/api/bkn-backend/v1/knowledge-networks/network-owned": {"tags": tags},
                         "/api/vega-backend/v1/catalogs/catalog-owned": {"tags": tags},
                         f"{APPS}/app-1": {"id": "app-1", "status": "published"}}
        self.calls = []

    def api(self, method, path, body=None):
        self.calls.append((method, path))
        if method == "GET" and path.startswith("/api/vega-backend/v1/catalogs?"):
            return {"entries": []}
        if method == "GET":
            return self.platform.get(path)
        self.platform.pop(path, None)
        return {}

    def uninstall(self, apps):
        record = {"id": "inst-supply-chain", "attemptId": "old", "sample": "supply-chain", "version": "0.1.3",
                  "status": "installed", "historyComplete": True, "catalogId": "catalog-owned", "databaseRuntime": None,
                  "workshopApps": apps,
                  "resources": {"knowledgeNetworkId": "network-owned", "ownedExecution": {"toolboxes": [], "skills": []}}}
        write_json(self.state / "supply-chain.json", record)
        previous = _read_state(self.state, "supply-chain")
        prepare_uninstall(self.state, "supply-chain", "inst-supply-chain", "admin")
        begin_installation_attempt(self.state, _read_state(self.state, "supply-chain"), previous)
        execute_uninstall(self.state, "supply-chain", self.api, lambda args, body=None: SimpleNamespace(returncode=0, stdout=""))
        return _read_state(self.state, "supply-chain")

    def test_uninstall_deletes_the_recorded_apps(self):
        record = self.uninstall([{"id": "app-1", "name": "Kit schedule"}])
        self.assertEqual(record["status"], "uninstalled")
        self.assertIn(("DELETE", f"{APPS}/app-1"), self.calls)
        self.assertFalse(any(path.startswith(f"{APPS}/app-1/") for _, path in self.calls))
        self.assertNotIn("workshopApps", record)

    def test_an_invalid_app_receipt_deletes_nothing(self):
        record = self.uninstall([{"name": "no id"}])
        self.assertEqual(record["status"], "uninstall_failed")
        self.assertFalse([call for call in self.calls if call[0] == "DELETE"])


if __name__ == "__main__":
    unittest.main()
