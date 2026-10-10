"""Create the in-cluster MariaDB for one sample. Does not create a Catalog."""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import yaml

from installer.contract import OFFICIAL_SOURCE_REPO, discover_sample_dirs, load_sample, read_version

NAMESPACE = "openbkn-samples"
SWR_IMAGE = "swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples"
GHCR_IMAGE = "ghcr.io/openbkn-ai/bkn-samples"
DB_USER = "bkn_sample"
_IMAGE_TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_IMAGE_REFERENCE = re.compile(
    r"^[a-z0-9][a-z0-9.-]*(?::[0-9]{1,5})?/"
    r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*"
    r"@sha256:[0-9a-f]{64}$"
)
_MANIFEST_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


class DeployError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _run(kubectl, args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return kubectl(args, stdin)


def _sample(root: Path, name: str) -> tuple[Path, dict]:
    for sample_dir in discover_sample_dirs(root):
        document = load_sample(sample_dir)
        if document["metadata"]["name"] == name:
            return sample_dir, document
    raise DeployError("install_failed", f"unknown sample {name}")


def _default_storage_class(kubectl) -> str:
    result = _run(kubectl, ["get", "storageclass", "-o", "json"])
    if result.returncode != 0:
        raise DeployError("storage_class_missing", "cannot list StorageClass")
    classes = json.loads(result.stdout or "{}").get("items", [])
    for item in classes:
        annotations = item.get("metadata", {}).get("annotations", {})
        if annotations.get("storageclass.kubernetes.io/is-default-class") == "true":
            return item["metadata"]["name"]
    raise DeployError("storage_class_missing", "the cluster has no default StorageClass")


def _workload_name(sample: str) -> str:
    return f"bkn-sample-{sample}"


def _secret_exists(kubectl, name: str) -> bool:
    result = _run(kubectl, ["get", "secret", name, "-n", NAMESPACE, "-o", "name"])
    return result.returncode == 0


def _apply(kubectl, manifest: str) -> None:
    result = _run(kubectl, ["apply", "-f", "-"], manifest)
    if result.returncode != 0:
        raise DeployError("install_failed", (result.stderr or "kubectl apply failed").strip())


def _manifests(sample: str, database: str, version: str, image: str, root_password: str, user_password: str) -> str:
    name = _workload_name(sample)
    probe = (
        "mariadb -uroot -p\"$MARIADB_ROOT_PASSWORD\" -N -e "
        f"\"SELECT 1 FROM $MARIADB_DATABASE.bkn_sample_meta "
        f"WHERE status='ready' AND sample_version='{version}'\""
    )
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {NAMESPACE}
---
apiVersion: v1
kind: Secret
metadata:
  name: {name}
  namespace: {NAMESPACE}
  labels:
    app: bkn-sample
    bkn-sample: {sample}
type: Opaque
stringData:
  mariadb-root-password: {root_password}
  mariadb-password: {user_password}
  mariadb-user: {DB_USER}
---
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {NAMESPACE}
  labels:
    app: bkn-sample
    bkn-sample: {sample}
spec:
  type: ClusterIP
  selector:
    app: bkn-sample
    bkn-sample: {sample}
  ports:
    - name: mysql
      port: 3306
      targetPort: 3306
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {name}
  namespace: {NAMESPACE}
  labels:
    app: bkn-sample
    bkn-sample: {sample}
spec:
  serviceName: {name}
  replicas: 1
  selector:
    matchLabels:
      app: bkn-sample
      bkn-sample: {sample}
  template:
    metadata:
      labels:
        app: bkn-sample
        bkn-sample: {sample}
    spec:
      containers:
        - name: mariadb
          image: {image}
          env:
            - name: BKN_SAMPLE_ID
              value: {sample}
            - name: BKN_SAMPLE_VERSION
              value: "{version}"
            - name: MARIADB_DATABASE
              value: {database}
            - name: MARIADB_USER
              value: {DB_USER}
            - name: MARIADB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {name}
                  key: mariadb-password
            - name: MARIADB_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {name}
                  key: mariadb-root-password
          ports:
            - containerPort: 3306
          readinessProbe:
            exec:
              command: ["sh", "-c", {json.dumps(probe)}]
            periodSeconds: 10
            failureThreshold: 30
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
"""


def _data_unavailable(text: str) -> bool:
    return (
        "sample data unavailable" in text
        or "checksum mismatch" in text
        or "Permission denied: '/var/lib/bkn-samples'" in text
    )


def _pod_logs(kubectl, sample: str) -> str:
    current = _run(
        kubectl,
        ["logs", "-n", NAMESPACE, "-l", f"app=bkn-sample,bkn-sample={sample}", "--tail=80"],
    )
    previous = _run(
        kubectl,
        ["logs", "-n", NAMESPACE, "-l", f"app=bkn-sample,bkn-sample={sample}", "--previous", "--tail=80"],
    )
    return f"{current.stdout or ''}\n{previous.stdout or ''}"


def _discard_failed_data(kubectl, sample: str) -> None:
    """A failed first boot leaves a data directory that will not run the loader again."""
    name = _workload_name(sample)
    _run(kubectl, ["delete", "pod", f"{name}-0", "-n", NAMESPACE, "--wait=false"])
    _run(kubectl, ["delete", "pvc", f"data-{name}-0", "-n", NAMESPACE, "--wait=false"])


def _pod_state(kubectl, sample: str, image: str | None = None) -> str:
    result = _run(
        kubectl,
        [
            "get", "pods", "-n", NAMESPACE,
            "-l", f"app=bkn-sample,bkn-sample={sample}",
            "-o", "json",
        ],
    )
    if result.returncode != 0:
        return "pending"
    items = json.loads(result.stdout or "{}").get("items", [])
    if not items:
        return "pending"
    containers = items[0].get("spec", {}).get("containers") or []
    running_image = containers[0].get("image") if containers else ""
    if image and running_image and running_image != image:
        return "pending"
    statuses = items[0].get("status", {}).get("containerStatuses", [])
    if any(item.get("ready") for item in statuses):
        return "ready"
    for item in statuses:
        reason = item.get("state", {}).get("waiting", {}).get("reason", "")
        if reason in {"ImagePullBackOff", "ErrImagePull"}:
            return "image_pull_failed"
        terminated = item.get("state", {}).get("terminated") or item.get("lastState", {}).get("terminated") or {}
        if reason == "CrashLoopBackOff" or terminated.get("exitCode") not in (None, 0):
            if _data_unavailable(_pod_logs(kubectl, sample)):
                return "sample_data_unavailable"
    return "pending"


def _usable_digest(value: str | None) -> str | None:
    text = (value or "").strip().strip('"')
    return text if _DIGEST.fullmatch(text) else None


def _manifest_digest(image: str, tag: str, opener) -> str | None:
    """Return the multi-arch manifest digest, or None when the registry has no matching image."""
    host, repository = image.split("/", 1)
    headers = {"Accept": _MANIFEST_ACCEPT}
    if host == "ghcr.io":
        token_url = (
            "https://ghcr.io/token?service=ghcr.io&scope="
            + urllib.parse.quote(f"repository:{repository}:pull", safe="")
        )
        try:
            with opener(urllib.request.Request(token_url), timeout=10) as response:
                token = json.loads(response.read().decode("utf-8")).get("token", "")
        except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, KeyError):
            token = ""
        if token:
            headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"https://{host}/v2/{repository}/manifests/{urllib.parse.quote(tag, safe='')}",
        headers=headers,
        method="HEAD",
    )
    try:
        with opener(request, timeout=10) as response:
            digest = response.headers.get("Docker-Content-Digest")
    except (OSError, urllib.error.URLError, TimeoutError, AttributeError):
        return None
    return _usable_digest(digest)


def registry_digests(tag: str, opener=urllib.request.urlopen) -> tuple[str | None, str | None]:
    """Read the SWR and GHCR manifest digests for one pinned tag. A missing image is None."""
    return _manifest_digest(SWR_IMAGE, tag, opener), _manifest_digest(GHCR_IMAGE, tag, opener)


def _digests_conflict(swr_digest: str | None, ghcr_digest: str | None) -> bool:
    left = _usable_digest(swr_digest)
    right = _usable_digest(ghcr_digest)
    return bool(left and right and left != right)


def _switch_image(kubectl, sample: str, image: str) -> None:
    name = _workload_name(sample)
    patch = json.dumps(
        [{"op": "replace", "path": "/spec/template/spec/containers/0/image", "value": image}]
    )
    result = _run(
        kubectl,
        ["patch", "statefulset", name, "-n", NAMESPACE, "--type=json", "-p", patch],
    )
    if result.returncode != 0:
        raise DeployError("image_unavailable", "cannot switch the sample image to GHCR")
    _run(kubectl, ["delete", "pod", f"{name}-0", "-n", NAMESPACE, "--wait=false"])


def image_tag(version: str) -> str:
    """Return the published database image tag.

    A release uses VERSION. A main build sets BKN_SAMPLE_DATA_IMAGE_TAG to the
    same tag as the catalog image, because that image is not published as VERSION.
    """
    override = os.environ.get("BKN_SAMPLE_DATA_IMAGE_TAG", "").strip()
    tag = override or version
    if tag == "latest" or not _IMAGE_TAG.fullmatch(tag):
        raise DeployError("image_unavailable", "the sample image tag is not pinned")
    return tag


def configured_image_ref() -> str | None:
    """An administrator may pin the data image in deployment configuration."""
    reference = os.environ.get("BKN_SAMPLE_DATA_IMAGE_REF", "").strip()
    if not reference:
        return None
    if not _IMAGE_REFERENCE.fullmatch(reference):
        raise DeployError("image_unavailable", "configured data image requires a registry/repository@sha256 reference")
    return reference


def _assert_database_ownership(kubectl, sample, version, image):
    name = _workload_name(sample)
    expected = {"openbkn.ai/sample-id": sample, "openbkn.ai/sample-version": version,
                "openbkn.ai/sample-data-image": image}
    for kind, resource in (("statefulset", name), ("service", name), ("secret", name),
                           ("pvc", f"data-{name}-0")):
        result = _run(kubectl, ["get", kind, resource, "-n", NAMESPACE, "--ignore-not-found", "-o", "json"])
        if result.returncode != 0:
            raise DeployError("install_failed", "cannot check existing sample database resources")
        if not (result.stdout or "").strip():
            continue
        current = json.loads(result.stdout)
        annotations = current.get("metadata", {}).get("annotations", {})
        if any(annotations.get(key) != value for key, value in expected.items()):
            raise DeployError("ownership_conflict", "an existing database resource is not owned by this fixed release")
        if kind == "statefulset":
            containers = current.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            if len(containers) != 1 or containers[0].get("image") != image:
                raise DeployError("ownership_conflict", "existing sample database image differs")


def _owned_manifests(manifest, sample, version, image):
    annotations = {"openbkn.ai/sample-id": sample, "openbkn.ai/sample-version": version,
                   "openbkn.ai/sample-data-image": image}
    documents = list(yaml.safe_load_all(manifest))
    for document in documents:
        if document["kind"] == "Namespace":
            continue
        document["metadata"].setdefault("annotations", {}).update(annotations)
        if document["kind"] == "StatefulSet":
            for claim in document["spec"]["volumeClaimTemplates"]:
                claim["metadata"].setdefault("annotations", {}).update(annotations)
    return yaml.safe_dump_all(documents, sort_keys=False)


def deploy_database(
    root: Path,
    sample: str,
    kubectl,
    sleep=time.sleep,
    attempts: int = 120,
    poll_seconds: float = 5.0,
    digests=None,
    data_image_ref: str | None = None,
    require_ownership: bool = False,
) -> dict:
    """Apply the sample database and wait until it is ready. Never creates a Catalog."""
    _sample_dir, document = _sample(root, sample)
    version = read_version(root)
    database = document["spec"]["database"]["name"]
    _default_storage_class(kubectl)
    name = _workload_name(sample)
    if _secret_exists(kubectl, name):
        root_password = ""
        user_password = ""
        secret_manifest = ""
    else:
        root_password = secrets.token_urlsafe(24)
        user_password = secrets.token_urlsafe(24)
        secret_manifest = "create"
    image = data_image_ref if data_image_ref is not None else configured_image_ref()
    if image is not None and not _IMAGE_REFERENCE.fullmatch(image):
        raise DeployError("image_unavailable", "sample data image requires a fixed registry digest")
    ghcr_digest = None
    if image is None:
        tag = image_tag(version)
        lookup = registry_digests if digests is None else digests
        swr_digest, ghcr_digest = lookup(tag)
        if _digests_conflict(swr_digest, ghcr_digest):
            raise DeployError("image_unavailable", "SWR and GHCR manifest digests differ")
        swr_digest = _usable_digest(swr_digest)
        ghcr_digest = _usable_digest(ghcr_digest)
        if not swr_digest and not ghcr_digest:
            raise DeployError("image_unavailable", "no verified sample image digest is available")
        image = f"{SWR_IMAGE}@{swr_digest}" if swr_digest else f"{GHCR_IMAGE}@{ghcr_digest}"
    if require_ownership:
        _assert_database_ownership(kubectl, sample, version, image)
    manifest = _manifests(sample, database, version, image, root_password or "unused", user_password or "unused")
    if secret_manifest == "":
        parts = manifest.split("---\n")
        manifest = "---\n".join(part for part in parts if "kind: Secret" not in part)
    if require_ownership:
        manifest = _owned_manifests(manifest, sample, version, image)
    _apply(kubectl, manifest)
    # A mirror switch is allowed only when its independently resolved digest
    # matches the selected artifact. Never fall back to a mutable tag.
    ghcr = f"{GHCR_IMAGE}@{ghcr_digest}" if ghcr_digest else None
    switched = image == ghcr
    state = "pending"
    for _ in range(attempts):
        state = _pod_state(kubectl, sample, image)
        if state == "ready":
            break
        if state == "sample_data_unavailable":
            if not require_ownership:
                _discard_failed_data(kubectl, sample)
            raise DeployError(
                "sample_data_unavailable",
                "the sample data was not downloaded or did not match its lock file",
            )
        if state == "image_pull_failed" and not switched and ghcr:
            _switch_image(kubectl, sample, ghcr)
            switched = True
            image = ghcr
        sleep(poll_seconds)
    else:
        if state == "image_pull_failed":
            raise DeployError("image_unavailable", "neither SWR nor GHCR could provide the sample image")
        raise DeployError("database_not_ready", "the sample database did not become ready")
    if state != "ready":
        code = "image_unavailable" if state == "image_pull_failed" else "database_not_ready"
        raise DeployError(code, "the sample database did not become ready")
    return {
        "sample": sample,
        "version": version,
        "namespace": NAMESPACE,
        "service": name,
        "host": f"{name}.{NAMESPACE}.svc",
        "port": 3306,
        "database": database,
        "user": DB_USER,
        "image": image,
        "sourceRepo": OFFICIAL_SOURCE_REPO,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: deploy_database.py <sample>", file=sys.stderr)
        return 2

    def kubectl(cmd: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["kubectl", *cmd],
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )

    try:
        result = deploy_database(Path(__file__).resolve().parents[1], args[0], kubectl)
    except DeployError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    print(
        f"sample database ready host={result['host']} database={result['database']} "
        f"user={result['user']} image={result['image']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
