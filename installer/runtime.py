"""In-cluster install runtime. The database password stays out of returned errors."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
import signal
import sys

from installer.hook_process import run_hook

from installer import shared_database
from pathlib import Path

from installer.control_plane import ControlError, create_installation, retry_installation
from installer.deploy_database import NAMESPACE, DeployError, _sample, configured_image_ref, deploy_database
from installer.state_store import write_json
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


def sample_contract(root: Path, sample: str) -> tuple[int, dict, dict]:
    _sample_dir, document = _sample(root, sample)
    spec = document["spec"]
    return int(spec["database"]["expectedTables"]), spec["knowledgeNetwork"], spec["components"]


def caller_env(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        return {}
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return {}
    # Preserve the executor environment (especially PATH) when passing the
    # bearer token to hooks and the CLI.  Replacing it outright makes
    # subprocess hooks unable to resolve `openbkn` on local/offline installs.
    return {**os.environ, "BKN_TOKEN": token}


def _command_failure(completed) -> str:
    detail = (completed.stderr or completed.stdout or "").strip().replace("\n", " ")
    detail = re.sub(r'("password"\s*:\s*")(?:\\.|[^"\\])*"', r'\1***"', detail)
    if len(detail) > 400:
        detail = detail[:400]
    if not detail:
        return "openbkn command failed"
    return f"openbkn command failed: {detail}"


def openbkn_json(args: list[str], run, env: dict | None = None) -> dict:
    completed = run(["openbkn", "--json", *args], env)
    if completed.returncode != 0:
        raise ControlError("install_failed", _command_failure(completed))
    payload = json.loads(completed.stdout or "{}")
    if payload is None:
        return {}
    if not isinstance(payload, (dict, list)):
        raise ControlError("install_failed", "openbkn command failed")
    return payload


def run_platform_hook(root: Path, stage: str, payload: dict, run, env: dict | None = None, state_dir: Path | None = None) -> dict:
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
        if state_dir is not None:
            shared = state_dir / payload["sample"]
            shared.mkdir(parents=True, exist_ok=True, mode=0o700)
            shared.chmod(0o700)
            hook_env["BKN_SAMPLE_CONFIG"] = str(shared / "config.yaml")
            hook_env["BKN_SAMPLE_RECEIPT"] = str(shared / "owned-execution.json")
        completed = run_hook(sample_dir, script, run, hook_env)
        if output.is_file():
            try:
                result = json.loads(output.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                result = None
            if isinstance(result, dict) and (completed.returncode == 0 or result.get("ok") is False or result.get("code")):
                return result
        if completed.returncode != 0 or not output.is_file():
            return {"ok": False, "message": "platform hook failed"}
        return {"ok": False, "message": "platform hook failed"}


def _record_database_image(state_dir, sample, version, deployed):
    image = deployed.get("image")
    if not image:
        return
    current = _read_state(state_dir, sample)
    if not current:
        from installer.studio_api import _write_installing
        _write_installing(state_dir, sample, version, data_image_ref=image)
        return
    if current.get("dataImageRef") and current["dataImageRef"] != image:
        raise ApiError(409, "version_changed", "database image differs from the installation receipt")
    current["dataImageRef"] = image
    write_json(state_dir / f"{sample}.json", current)


def install_sample(*, sample: str, actor_role: str, state_dir: Path, root: Path, version: str, deploy, kubectl, run, authorization: str | None = None) -> dict:
    if actor_role != "admin":
        raise ApiError(403, "forbidden", "an administrator must install the sample")
    cli_env = caller_env(authorization)
    try:
        if not shared_database.configured():
            raise DeployError("runtime_upgrade_required", "The product sample database is not configured; upgrade the sample service Chart.")
        database = shared_database.prepare(root, sample, version, state_dir, run)
        expected_tables, knowledge_network, components = sample_contract(root, sample)
        record = create_installation(
            sample=sample,
            version=version,
            actor_role=actor_role,
            database=database,
            state_dir=state_dir,
            openbkn=lambda args: openbkn_json(args, run, cli_env),
            hook_runner=lambda stage, payload: run_platform_hook(root, stage, payload, run, cli_env, state_dir),
            expected_tables=expected_tables,
            knowledge_network=knowledge_network,
            components=components,
        )
    except DeployError as exc:
        _write_failed(state_dir, sample, version, exc.code, exc.message, stage="database")
        raise ApiError(500, exc.code, exc.message) from exc
    except ControlError as exc:
        status = 403 if exc.code == "forbidden" else 409 if exc.code in {"already_installed", "use_retry", "ownership_conflict"} else 500
        raise ApiError(status, exc.code, exc.message) from exc
    return installation_view(record, actor_role)


def retry_sample(*, sample: str, installation_id: str, actor_role: str, state_dir: Path, root: Path, version: str, deploy, kubectl, run, authorization: str | None = None, accepted: bool = False, data_image_ref: str | None = None) -> dict:
    current = _read_state(state_dir, sample)
    if not current or _installation_id(current) != installation_id:
        raise ApiError(404, "install_failed", "installation not found")
    if actor_role != "admin":
        raise ApiError(403, "forbidden", "an administrator must install the sample")
    if current.get("version") != version:
        raise ApiError(409, "version_changed", "retry requires the original installed artifacts")
    if current.get("status") != ("installing" if accepted else "failed"):
        raise ApiError(409, "already_installed" if current.get("status") == "installed" else "already_installing",
                       "only a failed installation can be retried")
    cli_env = caller_env(authorization)
    try:
        if not shared_database.configured():
            raise DeployError("runtime_upgrade_required", "The product sample database is not configured; upgrade the sample service Chart.")
        database = shared_database.prepare(root, sample, version, state_dir, run)
        expected_tables, knowledge_network, components = sample_contract(root, sample)
        record = retry_installation(
            sample=sample,
            version=version,
            actor_role=actor_role,
            database=database,
            state_dir=state_dir,
            openbkn=lambda args: openbkn_json(args, run, cli_env),
            hook_runner=lambda stage, payload: run_platform_hook(root, stage, payload, run, cli_env, state_dir),
            expected_tables=expected_tables,
            knowledge_network=knowledge_network,
            components=components,
            accepted=accepted,
        )
    except (DeployError, ControlError) as exc:
        if isinstance(exc, DeployError):
            _write_failed(state_dir, sample, version, exc.code, exc.message, stage="database")
        code = getattr(exc, "code", "install_failed")
        status = 409 if code in {"already_installed", "use_retry", "ownership_conflict"} else 500
        raise ApiError(status, code, exc.message) from exc
    return installation_view(record, actor_role)


def kubectl_run(argv: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["kubectl", "--request-timeout=20s", *argv], input=stdin, text=True, capture_output=True, check=False, timeout=30)


def process_run(argv: list[str], env: dict | None) -> subprocess.CompletedProcess:
    identity = (env or {}).get("_BKN_HOOK_UID")
    if identity is not None:
        if sys.platform != "linux" or os.geteuid() != 0:
            raise ControlError("hook_isolation_unavailable", "Sample hooks require the product's Linux installation runtime.")
        # Hook environments are an allowlist, never the parent service environment.
        merged = {key: value for key, value in env.items() if key != "_BKN_HOOK_UID"}
        identity_options = {"user": int(identity), "group": int(identity), "extra_groups": [], "umask": 0o077}
    else:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        identity_options = {}
    # Bound the whole hook process tree, including children spawned by shell scripts.
    with subprocess.Popen(argv, env=merged, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, start_new_session=True, **identity_options) as process:
        try:
            stdout, stderr = process.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ControlError("operation_timeout", "Sample operation timed out; retry the operation.") from None
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def deploy(root: Path, sample: str, data_image_ref: str | None = None,
           sample_release_version: str | None = None) -> dict:
    return deploy_database(root, sample, kubectl_run, data_image_ref=data_image_ref,
                           require_ownership=True, sample_release_version=sample_release_version)
