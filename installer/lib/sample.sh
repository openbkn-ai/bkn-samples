#!/usr/bin/env bash

SAMPLE_DIR=""
SAMPLE_ID=""
SAMPLE_DATABASE=""
SAMPLE_TABLES=""
SAMPLE_DOCKER_PORT=""
SAMPLE_VERSION=""
SAMPLE_DATA_VERSION=""
SAMPLE_KN_ID=""

sample_python() {
  python3 - "$@" <<'PY'
import json
import pathlib
import re
import sys
import yaml

root = pathlib.Path(sys.argv[1])
requested = sys.argv[2] if len(sys.argv) > 2 else None
entries = []
seen_names = set()
seen_aliases = set()
for path in sorted(root.glob("samples/*/sample.yaml")):
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    metadata = raw.get("metadata") or {}
    spec = raw.get("spec") or {}
    name = metadata.get("name")
    aliases = metadata.get("aliases") or []
    database = spec.get("database") or {}
    data = spec.get("data") or {}
    hooks = spec.get("hooks") or {}
    required_hooks = ("dbInit", "dbVerify", "platformInstall", "platformVerify")
    if raw.get("apiVersion") != "samples.openbkn.ai/v1alpha1" or raw.get("kind") != "Sample":
        raise SystemExit(f"invalid apiVersion or kind: {path}")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", name) or not isinstance(aliases, list):
        raise SystemExit(f"invalid manifest: {path}")
    if any(not isinstance(alias, str) or not alias for alias in aliases):
        raise SystemExit(f"invalid sample alias: {path}")
    if name in seen_names or name in seen_aliases or any(alias in seen_names or alias in seen_aliases for alias in aliases):
        raise SystemExit(f"duplicate sample name or alias: {path}")
    if database.get("engine") != "mariadb" or not database.get("name"):
        raise SystemExit(f"sample must declare a MariaDB database: {path}")
    if not isinstance(database.get("expectedTables"), int) or not isinstance(database.get("dockerPort"), int):
        raise SystemExit(f"sample database expectedTables and dockerPort must be integers: {path}")
    if data.get("mode") not in ("embedded", "runtime-download") or not data.get("version"):
        raise SystemExit(f"sample data declaration is invalid: {path}")
    if data.get("mode") == "runtime-download" and not data.get("lockFile"):
        raise SystemExit(f"runtime-download sample requires data.lockFile: {path}")
    version = spec.get("version")
    kn_id = (spec.get("knowledgeNetwork") or {}).get("id")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise SystemExit(f"sample version must be a semantic version: {path}")
    if not isinstance(data.get("version"), str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", data["version"]):
        raise SystemExit(f"sample data.version must be a semantic version: {path}")
    if not isinstance(kn_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", kn_id):
        raise SystemExit(f"sample knowledgeNetwork.id is invalid: {path}")
    for hook in required_hooks:
        target = hooks.get(hook)
        if not isinstance(target, str) or target.startswith("/") or ".." in pathlib.PurePosixPath(target).parts:
            raise SystemExit(f"invalid {hook} path: {path}")
        if not (path.parent / target).is_file():
            raise SystemExit(f"missing {hook} target: {path.parent / target}")
    seen_names.add(name)
    seen_aliases.update(aliases)
    if requested is None or requested == name or requested in aliases:
        entries.append({
            "path": str(path.parent),
            "name": name,
            "display_name": metadata.get("displayName", name),
            "aliases": aliases,
            "database": (spec.get("database") or {}).get("name"),
            "expected_tables": (spec.get("database") or {}).get("expectedTables"),
            "docker_port": (spec.get("database") or {}).get("dockerPort"),
            "version": spec.get("version"),
            "data_version": (spec.get("data") or {}).get("version"),
            "kn_id": (spec.get("knowledgeNetwork") or {}).get("id"),
        })
if requested is not None and len(entries) != 1:
    raise SystemExit(f"unknown or ambiguous sample: {requested}")
print(json.dumps(entries, ensure_ascii=False))
PY
}

list_samples() {
  local root="$1"
  require_command python3
  sample_python "$root" | python3 -c '
import json, sys
for item in json.load(sys.stdin):
    aliases = ", ".join(item["aliases"])
    print("{}\t{}\t{}".format(item["name"], item["display_name"], aliases))
'
}

load_sample() {
  local root="$1" requested="$2" payload
  require_command python3
  payload="$(sample_python "$root" "$requested")" || die "invalid sample manifest"
  SAMPLE_DIR="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["path"])')"
  SAMPLE_ID="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["name"])')"
  SAMPLE_DATABASE="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["database"])')"
  SAMPLE_TABLES="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["expected_tables"])')"
  # shellcheck disable=SC2034 # consumed by other installer modules after sourcing.
  SAMPLE_DOCKER_PORT="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["docker_port"])')"
  # shellcheck disable=SC2034 # consumed by the runtime modules.
  SAMPLE_VERSION="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["version"])')"
  # shellcheck disable=SC2034 # consumed by the runtime modules.
  SAMPLE_DATA_VERSION="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["data_version"])')"
  # shellcheck disable=SC2034 # consumed by platform.sh.
  SAMPLE_KN_ID="$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["kn_id"])')"
}

print_install_plan() {
  local runtime="$1" host="$2" port="$3" namespace="$4" upgrade="$5"
  printf 'sample: %s (%s)\n' "$SAMPLE_ID" "$SAMPLE_DIR"
  printf 'database: %s; expected tables: %s\n' "$SAMPLE_DATABASE" "$SAMPLE_TABLES"
  printf 'runtime: %s\n' "$runtime"
  if [[ "$runtime" == docker || "$runtime" == auto ]]; then
    printf 'docker catalog endpoint: %s:%s\n' "${host:-<required in docker mode>}" "$port"
  fi
  printf 'kubernetes namespace: %s\n' "$namespace"
  printf 'upgrade: %s\n' "$upgrade"
  printf 'plan: validate login, start the sample MariaDB runtime, test Vega connectivity, then bootstrap the platform assets\n'
}
