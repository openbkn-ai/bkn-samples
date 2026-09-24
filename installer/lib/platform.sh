#!/usr/bin/env bash

OPENBKN_CATALOG_ID=""

catalog_id_by_name() {
  local name="$1"
  openbkn --json vega catalog list --type physical --name "$name" --limit -1 | python3 -c '
import json, sys
payload = json.load(sys.stdin)
entries = payload.get("entries", payload) if isinstance(payload, dict) else payload
for entry in entries:
    if entry.get("name") == sys.argv[1]:
        print(entry["id"])
        break
' "$name"
}

ensure_sample_catalog() {
  local connector_file="$1" catalog_name="bkn-sample-$SAMPLE_ID"
  openbkn --json vega catalog test-connection-config --connector-type mysql \
    --connector-config-file "$connector_file" >/dev/null
  OPENBKN_CATALOG_ID="$(catalog_id_by_name "$catalog_name")"
  if [[ -z "$OPENBKN_CATALOG_ID" ]]; then
    OPENBKN_CATALOG_ID="$(openbkn --json vega catalog create \
      --name "$catalog_name" \
      --connector-type mysql \
      --connector-config-file "$connector_file" \
      --tags "bkn-samples,bkn-sample-$SAMPLE_ID" \
      --description "OpenBKN sample $SAMPLE_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
  fi
  [[ -n "$OPENBKN_CATALOG_ID" ]] || die "could not create or locate catalog $catalog_name"
  openbkn --json vega catalog enable "$OPENBKN_CATALOG_ID" >/dev/null || true
  openbkn --json vega catalog discover "$OPENBKN_CATALOG_ID" >/dev/null
  wait_for_catalog_resources "$OPENBKN_CATALOG_ID"
}

wait_for_catalog_resources() {
  local catalog_id="$1" attempt count
  attempt=0
  while (( attempt < 60 )); do
    ((attempt += 1))
    count="$(openbkn --json vega catalog resources "$catalog_id" --category table --limit -1 | python3 -c '
import json, sys
payload = json.load(sys.stdin)
entries = payload.get("entries", payload) if isinstance(payload, dict) else payload
print(len(entries) if isinstance(entries, list) else 0)
')"
    (( count >= SAMPLE_TABLES )) && return 0
    sleep 2
  done
  die "catalog discovery did not expose the expected $SAMPLE_TABLES sample tables"
}

write_platform_config() {
  local state_dir="$1" catalog_id="$2"
  local config="$state_dir/platform.yaml"
  cat >"$config" <<EOF
openbkn:
  kn_id: ${SAMPLE_KN_ID}
database:
  engine: mysql
  host: unused
  port: 3306
  database: ${SAMPLE_DATABASE}
  user: bkn_sample
  password: unused
  schema: ""
load:
  table_prefix: ""
vega:
  catalog_id: ${catalog_id}
  catalog_name: bkn-sample-${SAMPLE_ID}
  connector_type: mysql
bind:
  dry_run: false
EOF
  chmod 600 "$config"
  printf '%s\n' "$config"
}

bootstrap_platform() {
  local runtime="$1" catalog_host="$2" catalog_port="$3" namespace="$4"
  local state_dir password_file password connector_file connector_dir platform_config
  state_dir="$(state_root)/runtime/$SAMPLE_ID"
  password_file="$state_dir/database-password"
  [[ -f "$password_file" ]] || die "sample database password state is missing"
  password="$(<"$password_file")"
  if [[ "$runtime" == "k8s" ]]; then
    catalog_host="bkn-sample-$SAMPLE_ID.$namespace.svc"
    catalog_port=3306
  fi
  connector_file="$(write_connector_config "$state_dir" "$catalog_host" "$catalog_port" bkn_sample "$password" "$SAMPLE_DATABASE")"
  connector_dir="${connector_file%/config.json}"
  trap '[[ -z "${connector_dir:-}" ]] || rm -rf -- "$connector_dir"' EXIT INT TERM
  ensure_sample_catalog "$connector_file"
  platform_config="$(write_platform_config "$state_dir" "$OPENBKN_CATALOG_ID")"
  BKN_CATALOG_ID="$OPENBKN_CATALOG_ID" BKN_KN_ID="$SAMPLE_KN_ID" BKN_PLATFORM_CONFIG="$platform_config" \
    BKN_CONNECTOR_CONFIG_FILE="$connector_file" "$SAMPLE_DIR/platform/install.sh"
  BKN_CATALOG_ID="$OPENBKN_CATALOG_ID" BKN_KN_ID="$SAMPLE_KN_ID" BKN_PLATFORM_CONFIG="$platform_config" \
    "$SAMPLE_DIR/platform/verify.sh"
  rm -rf "$connector_dir"
  trap - EXIT INT TERM
  printf 'OpenBKN sample installed: BKN=%s Catalog=%s\n' "$SAMPLE_KN_ID" "$OPENBKN_CATALOG_ID"
}
