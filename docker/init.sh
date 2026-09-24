#!/usr/bin/env bash
set -Eeuo pipefail

root=/opt/bkn-samples
# The first installable sample keeps its historical source directory. New
# samples use their manifest metadata.name as the image directory directly.
case "$BKN_SAMPLE_ID" in
  supply-chain) sample_dir="$root/samples/supply_ontology_hand" ;;
  *) sample_dir="$root/samples/$BKN_SAMPLE_ID" ;;
esac
ready_file=/var/lib/bkn-samples/ready.json

[[ -x "$sample_dir/db/init.sh" ]] || { echo "unsupported sample: $BKN_SAMPLE_ID" >&2; exit 1; }
"$sample_dir/db/init.sh"
"$sample_dir/db/verify.sh"

python3 - "$ready_file" <<PY
import json
import pathlib

path = pathlib.Path("$ready_file")
tmp = path.with_suffix(".tmp")
tmp.write_text(json.dumps({
  "sample_id": "$BKN_SAMPLE_ID",
  "sample_version": "${BKN_SAMPLE_VERSION:-1.0.0}",
  "data_version": "${BKN_DATA_VERSION:-1.0.0}",
  "status": "ready",
}), encoding="utf-8")
tmp.replace(path)
PY
chown mysql:mysql "$ready_file"
