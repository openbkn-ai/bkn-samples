"""samples.openbkn.ai/v1alpha1 contract checks and manifest index."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

OFFICIAL_SOURCE_REPO = "https://github.com/openbkn-ai/bkn-samples"
API_VERSION = "samples.openbkn.ai/v1alpha1"
NAME_RE = re.compile(r"^[a-z0-9-]{1,32}$")
DB_NAME_RE = re.compile(r"^[a-z0-9_]{1,64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_HOOKS = ("dbInit", "dbVerify", "platformInstall", "platformVerify")
COMPONENT_KEYS = ("objects", "relations", "metrics", "functions", "skills")
DB_HOOKS = ("dbInit", "dbVerify", "dbUpgrade")


class ContractError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def read_version(root: Path) -> str:
    text = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", text):
        raise ContractError([f"VERSION must be MAJOR.MINOR.PATCH, got {text!r}"])
    return text


def discover_sample_dirs(root: Path) -> list[Path]:
    samples = root / "samples"
    return sorted(path.parent for path in samples.glob("*/sample.yaml"))


def load_sample(sample_dir: Path) -> dict:
    path = sample_dir / "sample.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ContractError([f"{path}: sample.yaml must be a mapping"])
    return document


def _require_mapping(value, label: str, errors: list[str]) -> dict:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a mapping")
        return {}
    return value


def _hook_path(sample_dir: Path, raw: str, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw:
        errors.append(f"{label} must be a relative path")
        return None
    if raw.startswith("/") or "\\" in raw or ".." in Path(raw).parts:
        errors.append(f"{label} must stay inside the sample directory: {raw}")
        return None
    path = (sample_dir / raw).resolve()
    try:
        path.relative_to(sample_dir.resolve())
    except ValueError:
        errors.append(f"{label} escapes the sample directory: {raw}")
        return None
    if not path.is_file():
        errors.append(f"{label} does not exist: {raw}")
        return None
    return path


def validate_document(sample_dir: Path, document: dict) -> list[str]:
    errors: list[str] = []
    if document.get("apiVersion") != API_VERSION:
        errors.append(f"apiVersion must be {API_VERSION}")
    if document.get("kind") != "Sample":
        errors.append("kind must be Sample")
    metadata = _require_mapping(document.get("metadata"), "metadata", errors)
    name = metadata.get("name")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        errors.append("metadata.name must match [a-z0-9-]{1,32}")
    for field in ("displayName", "summary"):
        if not isinstance(metadata.get(field), str) or not metadata.get(field).strip():
            errors.append(f"metadata.{field} is required")
    aliases = metadata.get("aliases", [])
    if aliases is None:
        aliases = []
    if not isinstance(aliases, list):
        errors.append("metadata.aliases must be a list")
        aliases = []
    for alias in aliases:
        if not isinstance(alias, str) or not NAME_RE.fullmatch(alias):
            errors.append(f"alias is invalid: {alias!r}")

    spec = _require_mapping(document.get("spec"), "spec", errors)
    studio = _require_mapping(spec.get("studio"), "spec.studio", errors)
    if not isinstance(studio.get("licenseNote"), str) or not studio.get("licenseNote", "").strip():
        errors.append("spec.studio.licenseNote is required")
    questions = studio.get("questions", [])
    if not isinstance(questions, list) or len(questions) > 3:
        errors.append("spec.studio.questions must be a list of at most 3")
    elif any(not isinstance(item, str) or not item.strip() for item in questions):
        errors.append("spec.studio.questions entries must be non-empty strings")

    database = _require_mapping(spec.get("database"), "spec.database", errors)
    if database.get("engine") != "mariadb":
        errors.append("spec.database.engine must be mariadb")
    db_name = database.get("name")
    if not isinstance(db_name, str) or not DB_NAME_RE.fullmatch(db_name):
        errors.append("spec.database.name must match [a-z0-9_]{1,64}")
    tables = database.get("expectedTables")
    if not isinstance(tables, int) or isinstance(tables, bool) or tables < 1:
        errors.append("spec.database.expectedTables must be an integer >= 1")

    data = _require_mapping(spec.get("data"), "spec.data", errors)
    mode = data.get("mode")
    if mode == "embedded":
        if not (sample_dir / "data").is_dir():
            errors.append("embedded samples must include a data/ directory")
    elif mode == "runtime-download":
        lock = data.get("lockFile")
        _hook_path(sample_dir, lock, "spec.data.lockFile", errors)
    else:
        errors.append("spec.data.mode must be embedded or runtime-download")

    network = _require_mapping(spec.get("knowledgeNetwork"), "spec.knowledgeNetwork", errors)
    for field in ("id", "displayName"):
        if not isinstance(network.get(field), str) or not network.get(field, "").strip():
            errors.append(f"spec.knowledgeNetwork.{field} is required")

    capabilities = _require_mapping(spec.get("capabilities"), "spec.capabilities", errors)
    if not isinstance(capabilities.get("required"), bool):
        errors.append("spec.capabilities.required must be a boolean")
    components = _require_mapping(spec.get("components"), "spec.components", errors)
    for key in COMPONENT_KEYS:
        if not isinstance(components.get(key), bool):
            errors.append(f"spec.components.{key} must be a boolean")
    publishes = bool(components.get("functions")) or bool(components.get("skills"))
    if capabilities.get("required") is True and not publishes:
        errors.append("spec.capabilities.required cannot be true when the sample publishes neither functions nor skills")
    if capabilities.get("required") is False and publishes:
        errors.append("spec.capabilities.required must be true when the sample publishes functions or skills")

    hooks = _require_mapping(spec.get("hooks"), "spec.hooks", errors)
    for key in REQUIRED_HOOKS:
        _hook_path(sample_dir, hooks.get(key), f"spec.hooks.{key}", errors)
    if "dbUpgrade" in hooks:
        _hook_path(sample_dir, hooks.get("dbUpgrade"), "spec.hooks.dbUpgrade", errors)
    return errors


def validate_repository(root: Path) -> list[dict]:
    errors: list[str] = []
    loaded: list[tuple[Path, dict]] = []
    for sample_dir in discover_sample_dirs(root):
        try:
            document = load_sample(sample_dir)
        except ContractError as exc:
            errors.extend(f"{sample_dir.name}: {item}" for item in exc.errors)
            continue
        item_errors = validate_document(sample_dir, document)
        errors.extend(f"{sample_dir.name}: {item}" for item in item_errors)
        if not item_errors:
            loaded.append((sample_dir, document))

    names: dict[str, str] = {}
    databases: dict[str, str] = {}
    for sample_dir, document in loaded:
        install_name = document["metadata"]["name"]
        keys = [install_name, *document["metadata"].get("aliases", [])]
        for key in keys:
            if key in names:
                errors.append(f"name or alias {key} is used by both {names[key]} and {install_name}")
            else:
                names[key] = install_name
        db_name = document["spec"]["database"]["name"]
        if db_name in databases:
            errors.append(f"database {db_name} is used by both {databases[db_name]} and {install_name}")
        else:
            databases[db_name] = install_name
    if errors:
        raise ContractError(errors)
    return [document for _, document in loaded]


def manifest_sha256(sample_dir: Path, document: dict) -> str:
    hooks = document["spec"]["hooks"]
    relative_paths = ["sample.yaml"]
    relative_paths.extend(hooks[key] for key in DB_HOOKS if key in hooks)
    digest = hashlib.sha256()
    for relative in sorted(relative_paths):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((sample_dir / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_manifest_index(root: Path, revision: str, source_repo: str = OFFICIAL_SOURCE_REPO) -> dict:
    if source_repo != OFFICIAL_SOURCE_REPO:
        raise ContractError([f"sourceRepo must be {OFFICIAL_SOURCE_REPO}"])
    if not REVISION_RE.fullmatch(revision):
        raise ContractError(["sourceRevision must be a 40-character git commit"])
    version = read_version(root)
    samples = []
    for sample_dir in discover_sample_dirs(root):
        document = load_sample(sample_dir)
        item_errors = validate_document(sample_dir, document)
        if item_errors:
            raise ContractError([f"{sample_dir.name}: {item}" for item in item_errors])
        studio = document["spec"]["studio"]
        database = document["spec"]["database"]
        network = document["spec"]["knowledgeNetwork"]
        samples.append(
            {
                "name": document["metadata"]["name"],
                "displayName": document["metadata"]["displayName"],
                "summary": document["metadata"]["summary"],
                "licenseNote": studio["licenseNote"],
                "questions": list(studio["questions"]),
                "databaseName": database["name"],
                "expectedTables": database["expectedTables"],
                "dataMode": document["spec"]["data"]["mode"],
                "knowledgeNetworkId": network["id"],
                "knowledgeNetworkDisplayName": network["displayName"],
                "components": {key: bool(document["spec"]["components"][key]) for key in COMPONENT_KEYS},
                "manifestSha256": manifest_sha256(sample_dir, document),
            }
        )
    validate_repository(root)
    return {
        "apiVersion": API_VERSION,
        "version": version,
        "sourceRepo": source_repo,
        "sourceRevision": revision,
        "samples": samples,
    }


def check_manifest_index(root: Path, index: dict) -> None:
    errors: list[str] = []
    version = read_version(root)
    if index.get("apiVersion") != API_VERSION:
        errors.append(f"manifest apiVersion must be {API_VERSION}")
    if index.get("version") != version:
        errors.append(f"manifest version {index.get('version')!r} does not match VERSION {version}")
    if index.get("sourceRepo") != OFFICIAL_SOURCE_REPO:
        errors.append(f"sourceRepo must be {OFFICIAL_SOURCE_REPO}")
    if not isinstance(index.get("sourceRevision"), str) or not REVISION_RE.fullmatch(index.get("sourceRevision", "")):
        errors.append("sourceRevision must be a 40-character git commit")
    expected = build_manifest_index(root, index.get("sourceRevision") or "0" * 40)
    if index.get("samples") != expected["samples"]:
        errors.append("manifest samples do not match the repository sample.yaml files")
    if errors:
        raise ContractError(errors)


def write_manifest_index(root: Path, output: Path, revision: str) -> dict:
    index = build_manifest_index(root, revision)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index
