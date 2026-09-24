#!/usr/bin/env bash
set -Eeuo pipefail

: "${BKN_CATALOG_ID:?BKN_CATALOG_ID is required}"
openbkn --json vega catalog get "$BKN_CATALOG_ID" >/dev/null
openbkn --json bkn get worldcup_vega_catalog_bkn >/dev/null
