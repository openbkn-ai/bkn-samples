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

from installer.contract import OFFICIAL_SOURCE_REPO, discover_sample_dirs, load_sample, read_version

NAMESPACE = "openbkn-samples"
SWR_IMAGE = "swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples"
GHCR_IMAGE = "ghcr.io/openbkn-ai/bkn-samples"
DB_USER = "bkn_sample"
_IMAGE_TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
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
    return "sample data unavailable" in text or "checksum mismatch" in text


def _pod_logs(kubectl, sample: str) -> str:
    result = _run(
        kubectl,
        ["logs", "-n", NAMESPACE, "-l", f"app=bkn-sample,bkn-sample={sample}", "--tail=80"],
    )
    return result.stdout or ""


def _pod_state(kubectl, sample: str) -> str:
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


def deploy_database(
    root: Path,
    sample: str,
    kubectl,
    sleep=time.sleep,
    attempts: int = 30,
    digests=None,
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
    image = f"{SWR_IMAGE}:{image_tag(version)}"
    manifest = _manifests(sample, database, version, image, root_password or "unused", user_password or "unused")
    if secret_manifest == "":
        parts = manifest.split("---\n")
        manifest = "---\n".join(part for part in parts if "kind: Secret" not in part)
    _apply(kubectl, manifest)
    ghcr = f"{GHCR_IMAGE}:{image_tag(version)}"
    switched = False
    state = "pending"
    for _ in range(attempts):
        state = _pod_state(kubectl, sample)
        if state == "ready":
            break
        if state == "sample_data_unavailable":
            raise DeployError(
                "sample_data_unavailable",
                "the sample data was not downloaded or did not match its lock file",
            )
        if state == "image_pull_failed" and not switched:
            lookup = registry_digests if digests is None else digests
            swr_digest, ghcr_digest = lookup(image_tag(version))
            if _digests_conflict(swr_digest, ghcr_digest):
                raise DeployError("image_unavailable", "SWR and GHCR manifest digests differ")
            _switch_image(kubectl, sample, ghcr)
            switched = True
            image = ghcr
        sleep(0)
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
