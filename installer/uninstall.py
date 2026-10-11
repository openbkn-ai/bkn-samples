"""Official sample uninstall: fixed recorded IDs, checked ownership, persistent progress."""
import json
import os
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from installer.control_plane import ownership_tags
from installer.deploy_database import NAMESPACE, _workload_name
from installer.history import record_terminal_installation
from installer.state_store import write_json
from installer.studio_api import ApiError, _read_state, timestamp

SUPPORTED_SAMPLES = {"supply-chain", "world-cup", "order-basics"}

UNINSTALL_STAGES = (("knowledge", "删除知识网络和指标"), ("capabilities", "删除函数和 Skill"),
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


def prepare_uninstall(state_dir, sample, installation_id, role):
    if role != "admin":
        raise ApiError(403, "forbidden", "An administrator must uninstall the sample.")
    record = _read_state(state_dir, sample) or {}
    if sample not in SUPPORTED_SAMPLES or record.get("id") != installation_id:
        raise ApiError(404, "uninstall_failed", "Sample installation not found.")
    if record.get("status") not in {"installed", "uninstall_failed"}:
        raise ApiError(409, "already_installing", "Only an installed sample or a failed uninstall can be uninstalled.")
    resources = record.get("resources") or {}
    receipt = resources.get("ownedExecution")
    if not isinstance(receipt, dict) or any(not isinstance(receipt.get(k), list) for k in ("toolboxes", "skills")):
        raise ApiError(409, "ownership_receipt_missing", "This installation has no execution resource ownership receipt; automatic uninstall is unavailable.")
    record_terminal_installation(state_dir, record)
    record.update(status="uninstalling", operation="uninstall", stages={})
    record.pop("error", None)
    write_json(state_dir / f"{sample}.json", record)


def execute_uninstall(state_dir, sample, api, kubectl):
    record = _read_state(state_dir, sample)
    destination = state_dir / f"{sample}.json"
    def checkpoint(stage, state):
        record["stages"][stage] = state
        write_json(destination, record)
    try:
        resources = record["resources"]
        network_path = _path("/api/bkn-backend/v1/knowledge-networks/", resources.get("knowledgeNetworkId"))
        catalog_path = _path("/api/vega-backend/v1/catalogs/", record.get("catalogId"))
        required = set(ownership_tags(sample, record["version"]))
        # Validate every resource before the first deletion. Missing IDs are already removed.
        for path in (network_path, catalog_path):
            value = _single(api("GET", path))
            if value is not None and not required.issubset(set(value.get("tags") or [])):
                raise ApiError(409, "ownership_conflict", "A resource no longer belongs to this sample; nothing will be deleted.")
        execution_paths = [_path("/api/agent-operator-integration/v1/skills/", id_)
                           for id_ in resources["ownedExecution"]["skills"]]
        execution_paths += [_path("/api/agent-operator-integration/v1/tool-box/", id_)
                            for id_ in resources["ownedExecution"]["toolboxes"]]
        name = _workload_name(sample)
        database_resources = []
        for kind, resource in (("statefulset", name), ("service", name), ("secret", name), ("pvc", f"data-{name}-0")):
            result = kubectl(["get", kind, resource, "-n", NAMESPACE, "--ignore-not-found", "-o", "json"])
            if result.returncode:
                raise ApiError(500, "uninstall_failed", "Cannot check sample database ownership.")
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
        if _single(api("GET", network_path)) is not None:
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
        for stage, paths in (("knowledge", metrics + [network_path]), ("capabilities", execution_paths), ("discover", [catalog_path])):
            checkpoint(stage, "running")
            for path in paths:
                if stage == "capabilities":
                    resource = _single(api("GET", path))
                    if resource and resource.get("status") == "published":
                        method = "PUT" if "/skills/" in path else "POST"
                        api(method, path + "/status", {"status": "offline"})
                api("DELETE", path)
                if _single(api("GET", path)) is not None:
                    raise ApiError(500, "uninstall_failed", "Resource deletion has not completed; retry the uninstall.")
            checkpoint(stage, "succeeded")
        checkpoint("database", "running")
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
        for filename in ("owned-execution.json", "config.yaml"):
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
