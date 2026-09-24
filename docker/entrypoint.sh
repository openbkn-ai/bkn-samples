#!/usr/bin/env bash
set -Eeuo pipefail

sample_root=/var/lib/bkn-samples
owner_file="$sample_root/owner.json"
ready_file="$sample_root/ready.json"
data_dir="$sample_root/mysql"
failed_dir="$sample_root/failed"

fail_wait() {
  printf '%s\n' "$1" >&2
  # The next install invocation changes BKN_INIT_ATTEMPT and recreates this
  # container. Waiting avoids an automatic runtime restart loop.
  exec sleep infinity
}

[[ -n "${BKN_SAMPLE_ID:-}" ]] || { echo "BKN_SAMPLE_ID is required" >&2; exit 1; }
[[ -n "${BKN_DATABASE:-}" ]] || { echo "BKN_DATABASE is required" >&2; exit 1; }
[[ -n "${BKN_INIT_ATTEMPT:-}" ]] || { echo "BKN_INIT_ATTEMPT is required" >&2; exit 1; }

mkdir -p "$sample_root" "$failed_dir"

if [[ -f "$ready_file" ]]; then
  exec /usr/local/bin/docker-entrypoint.sh "$@"
fi

if [[ -e "$owner_file" ]]; then
  owner_sample="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sample_id"])' "$owner_file" 2>/dev/null || true)"
  owner_attempt="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["attempt_id"])' "$owner_file" 2>/dev/null || true)"
  [[ "$owner_sample" == "$BKN_SAMPLE_ID" && -n "$owner_attempt" ]] || fail_wait \
    "sample volume ownership marker is invalid or belongs to another sample; refusing to modify it"
  if [[ "$owner_attempt" == "$BKN_INIT_ATTEMPT" ]]; then
    fail_wait "previous initialization attempt $owner_attempt did not complete; re-run install.sh to retry safely"
  fi
  if [[ -e "$data_dir" ]]; then
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    rm -rf "$failed_dir/previous" 2>/dev/null || true
    mv "$data_dir" "$failed_dir/previous"
    printf '%s\n' "$stamp" >"$failed_dir/previous/failed-at"
  fi
else
  if [[ -n "$(find "$sample_root" -mindepth 1 -maxdepth 1 ! -name mysql ! -name cache ! -name failed -print -quit)" ]]; then
    echo "sample volume is non-empty without an ownership marker; refusing to modify it" >&2
    exit 1
  fi
fi

mkdir -p "$data_dir" "$sample_root/cache"
python3 - "$owner_file" <<PY
import json
import pathlib

path = pathlib.Path("$owner_file")
tmp = path.with_suffix(".tmp")
tmp.write_text(json.dumps({"sample_id": "$BKN_SAMPLE_ID", "attempt_id": "$BKN_INIT_ATTEMPT"}), encoding="utf-8")
tmp.replace(path)
PY
chown -R mysql:mysql "$sample_root"
exec /usr/local/bin/docker-entrypoint.sh "$@"
