#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${BKN_CATALOG_ID:?BKN_CATALOG_ID is required}"

cd "$root"
VEGA_CATALOG_ID="$BKN_CATALOG_ID" VEGA_SKIP_CREATE=1 DO_INDEX="${DO_INDEX:-1}" \
  DO_TOOLBOX="${DO_TOOLBOX:-1}" ./run.sh --from 4
