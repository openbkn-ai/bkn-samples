"""Create the in-cluster MariaDB for one sample. Does not create a Catalog."""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

from installer.contract import OFFICIAL_SOURCE_REPO, discover_sample_dirs, load_sample, read_version

NAMESPACE = "openbkn-samples"
SWR_IMAGE = "swr.cn-east-3.myhuaweicloud.com/openbkn-ai/bkn-samples"
GHCR_IMAGE = "ghcr.io/openbkn-ai/bkn-samples"
DB_USER = "bkn_sample"


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
    return "pending"


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


def deploy_database(root: Path, sample: str, kubectl, sleep=time.sleep, attempts: int = 30) -> dict:
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
    image = f"{SWR_IMAGE}:{version}"
    manifest = _manifests(sample, database, version, image, root_password or "unused", user_password or "unused")
    if secret_manifest == "":
        parts = manifest.split("---\n")
        manifest = "---\n".join(part for part in parts if "kind: Secret" not in part)
    _apply(kubectl, manifest)
    ghcr = f"{GHCR_IMAGE}:{version}"
    switched = False
    state = "pending"
    for _ in range(attempts):
        state = _pod_state(kubectl, sample)
        if state == "ready":
            break
        if state == "image_pull_failed" and not switched:
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
