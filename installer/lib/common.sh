#!/usr/bin/env bash

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

validate_runtime() {
  case "$1" in auto|docker|k8s) ;; *) die "--runtime must be auto, docker, or k8s" ;; esac
}

validate_port() {
  if [[ ! "$1" =~ ^[0-9]+$ ]] || (( 10#$1 < 1 || 10#$1 > 65535 )); then
    die "invalid port: $1"
  fi
}

validate_k8s_name() {
  local value="$1" label="$2"
  if [[ ! "$value" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || ((${#value} > 63)); then
    die "invalid $label: $value"
  fi
}

require_python_311() {
  require_command python3
  python3 - <<'PY' || exit 1
import sys
if sys.version_info < (3, 11):
    raise SystemExit("error: Python 3.11+ is required")
PY
}

prepare_python_env() {
  local root="$1" venv
  mkdir -p "$(state_root)"
  chmod 700 "$(state_root)"
  venv="$(state_root)/venv"
  if [[ ! -x "$venv/bin/python3" ]] || ! "$venv/bin/python3" -m pip --version >/dev/null 2>&1; then
    printf 'preparing isolated Python environment…\n'
    python3 -m venv --clear "$venv" || die \
      "could not create Python virtual environment at $venv; on Debian/Ubuntu install the matching python3-venv package (for example: sudo apt-get install python3-venv)"
  fi
  "$venv/bin/python3" -m pip install --disable-pip-version-check --quiet \
    -r "$root/samples/supply_ontology_hand/tools/requirements.txt" || die \
    "could not install sample Python dependencies"
  export PATH="$venv/bin:$PATH"
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    python3 - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
  fi
}

state_root() {
  printf '%s/.bkn-samples\n' "$PWD"
}
