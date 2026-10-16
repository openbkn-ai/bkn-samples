"""Sample uninstall using recorded resource IDs, ownership checks and progress."""
import json
import os
import re
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, HTTPRedirectHandler, ProxyHandler, build_opener

import yaml

from installer import shared_database
from installer.control_plane import catalog_name, ownership_tags
from installer.deploy_database import NAMESPACE, _workload_name, database_read_error
from installer.history import read_installation_history, record_terminal_installation
from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, timestamp

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


# Cleanup only contacts the configured platform endpoint. Do not route through
# a workstation proxy or follow an internal API redirect to an external site.
urlopen = build_opener(ProxyHandler({}), _NoRedirect()).open

SAMPLE_NAME_RE = re.compile(r"^[a-z0-9-]{1,32}$")

UNINSTALL_STAGES = (("preflight", "检查样例资源归属"), ("knowledge", "删除知识网络和指标"), ("capabilities", "删除函数和 Skill"),
                    ("discover", "删除数据源"), ("database", "删除样例库和存储"), ("verify", "验证清理结果"))


def platform_client(authorization):
    base = os.environ["BKN_BASE_URL"].rstrip("/")
    def call(method, path, body=None):
        request = Request(base + path, method=method,
                          data=json.dumps(body).encode() if body is not None else None,
                          headers={"Authorization": authorization, "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except HTTPError as error:
            if error.code == 404:
                return None
            raise ApiError(500, "uninstall_failed", "Platform resource operation failed; retry the uninstall.") from None
    return call


def _single(value):
    if isinstance(value, dict) and "entries" in value:
        entries = value["entries"]
        if isinstance(entries, list) and len(entries) <= 1:
            return entries[0] if entries else None
        raise ApiError(500, "uninstall_failed", "Ambiguous resource response.")
    if value is not None and not isinstance(value, dict):
        raise ApiError(500, "uninstall_failed", "Invalid resource response.")
    return value


def _path(prefix, resource_id):
    if not isinstance(resource_id, str) or not resource_id:
        raise ApiError(409, "ownership_conflict", "The sample resource receipt is incomplete.")
    return prefix + quote(resource_id, safe="")


def _failed_resources(state_dir, sample, record):
    """Recover only this installation's local receipts, never infer ownership from a new package."""
    resources = dict(record.get("resources") or {})
    shared = state_dir / sample
    history, _ = read_installation_history(state_dir, sample, record)
    hook_started = any(
        any(stage in (attempt.get("stages") or {}) for stage in ("knowledge", "capabilities", "verify"))
        for attempt in [record, *history]
        if attempt.get("id") == record.get("id") and attempt.get("operation") != "uninstall"
    )
    hook_started = hook_started or bool(resources.get("knowledgeNetworkId"))
    catalog_id = record.get("catalogId")
    try:
        if (shared / "config.yaml").exists():
            config = yaml.safe_load((shared / "config.yaml").read_text())
            if (resources.get("knowledgeNetworkId") not in (None, config["openbkn"]["kn_id"])
                    or catalog_id not in (None, config["vega"]["catalog_id"])):
                raise ValueError("local configuration differs from installation receipt")
            resources.setdefault("knowledgeNetworkId", config["openbkn"]["kn_id"])
            catalog_id = catalog_id or config["vega"]["catalog_id"]
            hook_started = True
        receipts = [resources["ownedExecution"]] if "ownedExecution" in resources else []
        if (shared / "owned-execution.json").exists():
            receipts.append(json.loads((shared / "owned-execution.json").read_text()))
            hook_started = True
        if hook_started and (not resources.get("knowledgeNetworkId") or not receipts):
            raise ValueError("missing hook receipt")
        owned = {"toolboxes": [], "skills": []}
        for receipt in receipts:
            for kind in owned:
                ids = receipt[kind]
                if not isinstance(ids, list) or any(not isinstance(id_, str) or not id_ for id_ in ids):
                    raise ValueError("invalid hook receipt")
                owned[kind] = list(dict.fromkeys([*owned[kind], *ids]))
        resources["ownedExecution"] = owned
        resources.setdefault("knowledgeNetworkId", None)
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError):
        raise ApiError(409, "ownership_receipt_missing", "The failed installation resource receipt is incomplete; nothing will be deleted.") from None
    return resources, catalog_id


def prepare_uninstall(state_dir, sample, installation_id, role):
    if role != "admin":
        raise ApiError(403, "forbidden", "An administrator must uninstall the sample.")
    record = _read_state(state_dir, sample) or {}
    # Samples are registered through the catalog at runtime.  The installation
    # record and its ownership receipt are the authority; do not maintain a
    # second static allowlist here.
    if not SAMPLE_NAME_RE.fullmatch(sample) or record.get("sample") != sample or record.get("id") != installation_id:
        raise ApiError(404, "uninstall_failed", "Sample installation not found.")
    if record.get("status") not in {"installed", "failed", "uninstall_failed"}:
        raise ApiError(409, "already_installing", "Only an installed sample, a failed installation or a failed uninstall can be cleaned up.")
    failed_resources = _failed_resources(state_dir, sample, record) if record["status"] == "failed" else None
    resources = record.get("resources") or {}
    receipt = resources.get("ownedExecution")
    if failed_resources is None and (not isinstance(receipt, dict) or any(not isinstance(receipt.get(k), list) for k in ("toolboxes", "skills"))):
        raise ApiError(409, "ownership_receipt_missing", "This installation has no execution resource ownership receipt; automatic uninstall is unavailable.")
    record_terminal_installation(state_dir, record)
    if failed_resources is not None:
        record["resources"], record["catalogId"] = failed_resources
    record.update(status="uninstalling", operation="uninstall", stages={})
    record.pop("error", None)
    write_json(state_dir / f"{sample}.json", record)


def execute_uninstall(state_dir, sample, api, kubectl):
    record = _read_state(state_dir, sample)
    destination = state_dir / f"{sample}.json"
    deadline = time.monotonic() + 300
    original_api, original_kubectl = api, kubectl
    def remaining():
        if time.monotonic() >= deadline:
            raise ApiError(500, "uninstall_failed", "Uninstall timed out; continue cleanup to resume from the recorded resources.")
    def api(*args, **kwargs):
        remaining()
        return original_api(*args, **kwargs)
    def kubectl(*args, **kwargs):
        remaining()
        return original_kubectl(*args, **kwargs)
    def checkpoint(stage, state):
        record["stages"][stage] = state
        write_json(destination, record)
    try:
        checkpoint("preflight", "running")
        resources = record["resources"]
        network_id = resources["knowledgeNetworkId"]
        network_path = _path("/api/bkn-backend/v1/knowledge-networks/", network_id) if network_id else None
        if not record.get("catalogId"):
            name = catalog_name(sample)
            found = api("GET", "/api/vega-backend/v1/catalogs?name=" + quote(name, safe="") + "&limit=-1")
            if not isinstance(found, dict) or not isinstance(found.get("entries"), list) or any(not isinstance(item, dict) for item in found["entries"]):
                raise ApiError(500, "uninstall_failed", "Cannot check the failed installation catalog.")
            matches = [item for item in found["entries"] if item.get("name") == name]
            if len(matches) > 1:
                raise ApiError(409, "ownership_conflict", "The sample catalog is ambiguous; nothing will be deleted.")
            if matches:
                record["catalogId"] = matches[0].get("id")
                _path("/api/vega-backend/v1/catalogs/", record["catalogId"])
                write_json(destination, record)
        catalog_path = _path("/api/vega-backend/v1/catalogs/", record["catalogId"]) if record.get("catalogId") else None
        required = set(ownership_tags(sample, record["version"]))
        # Validate every resource before the first deletion. Missing IDs are already removed.
        for path in (network_path, catalog_path):
            if path is None:
                continue
            value = _single(api("GET", path))
            if value is not None and not required.issubset(set(value.get("tags") or [])):
                if path == network_path and resources.get("knowledgeNetworkPlanned") is True:
                    # A failed hook's intended target is not a receipt of ownership.
                    # Leave an unrelated existing network untouched and clean only owned resources.
                    network_path = None
                    continue
                raise ApiError(409, "ownership_conflict", "A resource no longer belongs to this sample; nothing will be deleted.")
        execution_paths = [_path("/api/agent-operator-integration/v1/skills/", id_)
                           for id_ in resources["ownedExecution"]["skills"]]
        execution_paths += [_path("/api/agent-operator-integration/v1/tool-box/", id_)
                            for id_ in resources["ownedExecution"]["toolboxes"]]
        name = _workload_name(sample)
        database_resources = []
        if record.get("databaseRuntime"):
            shared_database.validate_owner(record)
        else:
            for kind, resource in (("statefulset", name), ("service", name), ("secret", name), ("pvc", f"data-{name}-0")):
                result = kubectl(["get", kind, resource, "-n", NAMESPACE, "--ignore-not-found", "-o", "json"])
                if result.returncode:
                    raise database_read_error(result, kind)
                if not (result.stdout or "").strip():
                    continue
                value = json.loads(result.stdout)
                annotations = value.get("metadata", {}).get("annotations", {})
                expected = {"openbkn.ai/sample-id": sample, "openbkn.ai/sample-version": record["version"],
                            "openbkn.ai/sample-data-image": record.get("dataImageRef")}
                if not expected["openbkn.ai/sample-data-image"] or any(annotations.get(k) != v for k, v in expected.items()):
                    raise ApiError(409, "ownership_conflict", "Sample database ownership is missing or differs; nothing will be deleted.")
                database_resources.append((kind, resource, value["metadata"]["uid"]))
        # Metrics are owned by the network scope, including user edits in this sample.
        metrics = []
        if network_path and _single(api("GET", network_path)) is not None:
            offset = 0
            while True:
                page = api("GET", network_path + f"/metrics?limit=500&offset={offset}")
                if not isinstance(page, dict) or not isinstance(page.get("entries"), list):
                    raise ApiError(500, "uninstall_failed", "Cannot enumerate sample metrics.")
                entries = page["entries"]
                paths = [_path(network_path + "/metrics/", entry.get("id")) for entry in entries]
                if set(metrics).intersection(paths) or len(set(paths)) != len(paths):
                    raise ApiError(500, "uninstall_failed", "Invalid metric pagination.")
                metrics.extend(paths)
                if len(entries) < 500:
                    break
                offset += len(entries)
        checkpoint("preflight", "succeeded")
        for stage, paths in (("knowledge", metrics + ([network_path] if network_path else [])), ("capabilities", execution_paths), ("discover", [catalog_path] if catalog_path else [])):
            checkpoint(stage, "running")
            for path in paths:
                resource = _single(api("GET", path))
                if resource is None:
                    continue
                if stage == "capabilities":
                    if resource.get("status") == "published":
                        method = "PUT" if "/skills/" in path else "POST"
                        api(method, path + "/status", {"status": "offline"})
                api("DELETE", path)
                for attempt in range(10):
                    if _single(api("GET", path)) is None:
                        break
                    time.sleep(1)
                else:
                    raise ApiError(500, "uninstall_failed", "Resource deletion has not completed; continue the uninstall.")
            checkpoint(stage, "succeeded")
        checkpoint("database", "running")
        if record.get("databaseRuntime"):
            remaining()
            shared_database.remove(record)
        for kind, resource, uid in database_resources:
            # UID preconditions prevent deleting a replacement with the same name.
            group = "/apis/apps/v1" if kind == "statefulset" else "/api/v1"
            plural = {"statefulset": "statefulsets", "service": "services", "secret": "secrets", "pvc": "persistentvolumeclaims"}[kind]
            result = kubectl(["delete", "--raw", f"{group}/namespaces/{NAMESPACE}/{plural}/{resource}", "-f", "-"],
                             json.dumps({"apiVersion": "v1", "kind": "DeleteOptions", "preconditions": {"uid": uid}}))
            if result.returncode:
                raise ApiError(500, "uninstall_failed", "Sample database deletion failed; retry the uninstall.")
        checkpoint("database", "succeeded")
        checkpoint("verify", "running")
        for kind, resource, _uid in database_resources:
            for attempt in range(30):
                result = kubectl(["get", kind, resource, "-n", NAMESPACE, "--ignore-not-found", "-o", "name"])
                if result.returncode:
                    raise ApiError(500, "uninstall_failed", "Cannot verify database cleanup.")
                if not (result.stdout or "").strip():
                    break
                time.sleep(2)
            else:
                raise ApiError(500, "uninstall_failed", "Database cleanup is still pending; retry the uninstall.")
        checkpoint("verify", "succeeded")
        record.update(status="uninstalled", finishedAt=timestamp())
        record.pop("error", None)
        for filename in ("owned-execution.json", "config.yaml", "database-credentials.json"):
            (state_dir / sample / filename).unlink(missing_ok=True)
    except Exception as error:
        record.update(status="uninstall_failed", finishedAt=timestamp(),
                      error={"code": getattr(error, "code", "uninstall_failed"),
                             "message": getattr(error, "message", "Uninstall failed; retry the uninstall.")})
        for stage, value in record["stages"].items():
            if value == "running":
                record["stages"][stage] = "failed"
    write_json(destination, record)
    record_terminal_installation(state_dir, record)
