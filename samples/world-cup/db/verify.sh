#!/usr/bin/env bash
set -Eeuo pipefail

count="$(mariadb -N -uroot -p"$MARIADB_ROOT_PASSWORD" "$BKN_DATABASE" -e "
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_name LIKE 'wc\\_%';")"
[[ "$count" == "27" ]] || { echo "expected 27 World Cup tables, got $count" >&2; exit 1; }
mariadb -N -uroot -p"$MARIADB_ROOT_PASSWORD" "$BKN_DATABASE" \
  -e "SELECT COUNT(*) FROM bkn_sample_meta WHERE sample_id = 'world-cup' AND status = 'ready'" | grep -qx 1
