"""In-cluster install runtime. The database password stays out of returned errors."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from installer.control_plane import ControlError, create_installation, retry_installation
from installer.deploy_database import NAMESPACE, DeployError, _sample, deploy_database
from installer.studio_api import ApiError, _installation_id, _read_state, _write_failed, installation_view


def database_config(deployed: dict, kubectl) -> dict:
    result = kubectl(
        [
            "get",
            "secret",
            deployed["service"],
            "-n",
            deployed.get("namespace", NAMESPACE),
            "-o",
            "jsonpath={.data.mariadb-password}",
        ]
    )
    if result.returncode != 0 or not (result.stdout or "").strip():
        raise DeployError("database_not_ready", "the sample database secret is missing")
    return {
        "name": deployed["database"],
        "host": deployed["host"],
        "port": deployed["port"],
        "user": deployed["user"],
        "password": base64.b64decode(result.stdout).decode("utf-8"),
    }


def sample_contract(root: Path, sample: str) -> tuple[int, dict]:
    _sample_dir, document = _sample(root, sample)
    spec = document["spec"]
    return int(spec["database"]["expectedTables"]), spec["knowledgeNetwork"]


def caller_env(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        return {}
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return {}
    return {"BKN_TOKEN": token}


def openbkn_json(args: list[str], run, env: dict | None = None) -> dict:
    completed = run(["openbkn", "--json", *args], env)
    if completed.returncode != 0:
        raise ControlError("install_failed", "openbkn command failed")
    payload = json.loads(completed.stdout or "{}")
    if not isinstance(payload, (dict, list)):
        raise ControlError("install_failed", "openbkn command failed")
    return payload


def run_platform_hook(root: Path, stage: str, payload: dict, run, env: dict | None = None) -> dict:
    sample_dir, document = _sample(root, payload["sample"])
    hook_name = "platformInstall" if stage == "platform-install" else "platformVerify"
    script = sample_dir / document["spec"]["hooks"][hook_name]
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        source = directory / "input.json"
        output = directory / "output.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        hook_env = dict(env or {})
        hook_env["BKN_SAMPLE_INPUT"] = str(source)
        hook_env["BKN_SAMPLE_OUTPUT"] = str(output)
        completed = run([str(script)], hook_env)
        if completed.returncode != 0 or not output.is_file():
            return {"ok": False, "message": "platform hook failed"}
        result = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            return {"ok": False, "message": "platform hook failed"}
        return result


def install_sample(*, sample: str, actor_role: str, state_dir: Path, root: Path, version: str, deploy, kubectl, run, authorization: str | None = None) -> dict:
    if actor_role != "admin":
        raise ApiError(403, "forbidden", "an administrator must install the sample")
    cli_env = caller_env(authorization)
    try:
        deployed = deploy(sample)
        database = database_config(deployed, kubectl)
        expected_tables, knowledge_network = sample_contract(root, sample)
        record = create_installation(
            sample=sample,
            version=version,
            actor_role=actor_role,
            database=database,
            state_dir=state_dir,
            openbkn=lambda args: openbkn_json(args, run, cli_env),
            hook_runner=lambda stage, payload: run_platform_hook(root, stage, payload, run, cli_env),
            expected_tables=expected_tables,
            knowledge_network=knowledge_network,
        )
    except DeployError as exc:
        _write_failed(state_dir, sample, version, exc.code, exc.message)
        raise ApiError(500, exc.code, exc.message) from exc
    except ControlError as exc:
        status = 403 if exc.code == "forbidden" else 409 if exc.code in {"already_installed", "use_retry", "ownership_conflict"} else 500
        raise ApiError(status, exc.code, exc.message) from exc
    return installation_view(record, actor_role)


def retry_sample(*, sample: str, installation_id: str, actor_role: str, state_dir: Path, root: Path, version: str, deploy, kubectl, run, authorization: str | None = None) -> dict:
    current = _read_state(state_dir, sample)
    if not current or _installation_id(current) != installation_id:
        raise ApiError(404, "install_failed", "installation not found")
    if actor_role != "admin":
        raise ApiError(403, "forbidden", "an administrator must install the sample")
    cli_env = caller_env(authorization)
    try:
        deployed = deploy(sample)
        database = database_config(deployed, kubectl)
        expected_tables, knowledge_network = sample_contract(root, sample)
        record = retry_installation(
            sample=sample,
            version=version,
            actor_role=actor_role,
            database=database,
            state_dir=state_dir,
            openbkn=lambda args: openbkn_json(args, run, cli_env),
            hook_runner=lambda stage, payload: run_platform_hook(root, stage, payload, run, cli_env),
            expected_tables=expected_tables,
            knowledge_network=knowledge_network,
        )
    except (DeployError, ControlError) as exc:
        code = getattr(exc, "code", "install_failed")
        status = 409 if code in {"already_installed", "use_retry", "ownership_conflict"} else 500
        raise ApiError(status, code, exc.message) from exc
    return installation_view(record, actor_role)


def kubectl_run(argv: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["kubectl", *argv], input=stdin, text=True, capture_output=True, check=False)


def process_run(argv: list[str], env: dict | None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(argv, env=merged, text=True, capture_output=True, check=False)


def deploy(root: Path, sample: str) -> dict:
    return deploy_database(root, sample, kubectl_run)
