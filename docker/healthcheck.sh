#!/usr/bin/env bash
set -Eeuo pipefail

ready_file=/var/lib/bkn-samples/ready.json
[[ -s "$ready_file" ]] || exit 1
mariadb-admin ping -uroot -p"${MARIADB_ROOT_PASSWORD:?}" --silent >/dev/null
mariadb -N -uroot -p"${MARIADB_ROOT_PASSWORD:?}" "$MARIADB_DATABASE" \
  -e "SELECT 1 FROM bkn_sample_meta
      WHERE sample_id = '${BKN_SAMPLE_ID:?}'
        AND sample_version = '${BKN_SAMPLE_VERSION:?}'
        AND data_version = '${BKN_DATA_VERSION:?}'
        AND status = 'ready'
      LIMIT 1" | grep -qx 1
