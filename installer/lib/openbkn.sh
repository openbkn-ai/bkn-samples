#!/usr/bin/env bash

ensure_openbkn_login() {
  local base_url="$1"
  require_command openbkn
  if openbkn --json auth whoami >/dev/null 2>&1; then
    return 0
  fi

  if [[ ! -t 0 || ! -t 1 ]]; then
    if [[ -n "$base_url" ]]; then
      die "OpenBKN login is required: openbkn auth login $base_url --device"
    fi
    die "OpenBKN login is required: openbkn auth login <openbkn-url> --device"
  fi
  if [[ -z "$base_url" ]]; then
    read -r -p "OpenBKN URL: " base_url
  fi
  [[ -n "$base_url" ]] || die "OpenBKN URL is required for login"
  openbkn auth login "$base_url" --device
  openbkn --json auth whoami >/dev/null 2>&1 || die "OpenBKN login did not complete"
}

require_openbkn_safe_connector_input() {
  local help
  help="$(openbkn vega catalog create --help 2>&1)" || die "cannot inspect openbkn vega catalog create"
  grep -F -- '--connector-config-file' <<<"$help" >/dev/null || die \
    "this installer requires an openbkn CLI with --connector-config-file; upgrade the CLI before installing samples"
  help="$(openbkn vega catalog update --help 2>&1)" || die "cannot inspect openbkn vega catalog update"
  grep -F -- '--connector-config-file' <<<"$help" >/dev/null || die \
    "this installer requires --connector-config-file for catalog update"
  help="$(openbkn vega catalog test-connection-config --help 2>&1)" || die \
    "cannot inspect openbkn vega catalog test-connection-config"
  grep -F -- '--connector-config-file' <<<"$help" >/dev/null || die \
    "this installer requires --connector-config-file for connection tests"
}

write_connector_config() {
  local state_dir="$1" host="$2" port="$3" username="$4" password="$5" database="$6"
  local temp_dir
  temp_dir="$(mktemp -d "$state_dir/connector.XXXXXXXX")"
  chmod 700 "$temp_dir"
  python3 - "$temp_dir/config.json" "$host" "$port" "$username" "$database" 3<<<"$password" <<'PY'
import json
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
payload = {
    "host": sys.argv[2],
    "port": int(sys.argv[3]),
    "username": sys.argv[4],
    "password": os.fdopen(3).read().rstrip("\n"),
    "database": sys.argv[5],
}
path.write_text(json.dumps(payload), encoding="utf-8")
path.chmod(0o600)
PY
  printf '%s\n' "$temp_dir/config.json"
}
