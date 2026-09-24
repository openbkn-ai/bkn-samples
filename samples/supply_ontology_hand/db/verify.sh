#!/usr/bin/env bash
set -Eeuo pipefail

count="$(mariadb -N -uroot -p"$MARIADB_ROOT_PASSWORD" "$BKN_DATABASE" -e "
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_name <> 'bkn_sample_meta';")"
[[ "$count" == "12" ]] || { echo "expected 12 sample tables, got $count" >&2; exit 1; }
mariadb -N -uroot -p"$MARIADB_ROOT_PASSWORD" "$BKN_DATABASE" \
  -e "SELECT COUNT(*) FROM bkn_sample_meta WHERE sample_id = 'supply-chain' AND status = 'ready'" | grep -qx 1
