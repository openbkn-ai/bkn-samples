#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${BKN_CATALOG_ID:?BKN_CATALOG_ID is required}"
: "${BKN_PLATFORM_CONFIG:?BKN_PLATFORM_CONFIG is required}"

python3 "$root/tools/import_kn.py" --embedding-mode auto
python3 "$root/tools/bind_kn_resources.py" --config "$BKN_PLATFORM_CONFIG" --preserve-vector-config

function_report="$(python3 "$root/tools/register_native_function_toolbox.py" --apply)"
printf '%s\n' "$function_report"
function_box_id="$(printf '%s' "$function_report" | python3 -c 'import json,sys; print(json.load(sys.stdin)["box_id"])')"
openbkn --json bkn capability attach "$BKN_KN_ID" --box "$function_box_id" --all-tools >/dev/null

skill_report="$(python3 "$root/tools/register_skills.py" --apply)"
printf '%s\n' "$skill_report"
skill_ids="$(printf '%s' "$skill_report" | python3 -c 'import json,sys; print(",".join(item["skill_id"] for item in json.load(sys.stdin)["skills"]))')"
openbkn --json bkn capability attach "$BKN_KN_ID" --skill "$skill_ids" >/dev/null
