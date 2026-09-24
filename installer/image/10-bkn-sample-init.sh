#!/bin/sh
# First-boot dispatcher. MariaDB runs this only when the data directory is empty.
set -eu
sample_id="${BKN_SAMPLE_ID:-}"
root=/opt/bkn-samples/samples
case "$sample_id" in
  supply-chain)
    sample_dir="${root}/supply_ontology_hand"
    ;;
  world-cup)
    sample_dir="${root}/world-cup"
    ;;
  *)
    echo "BKN_SAMPLE_ID must be a sample shipped in this image" >&2
    exit 1
    ;;
esac
if [ -S /run/mysqld/mysqld.sock ]; then
  export MYSQL_UNIX_SOCKET=/run/mysqld/mysqld.sock
else
  export MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
  export MYSQL_PORT="${MYSQL_PORT:-3306}"
fi
export MYSQL_USER="${MYSQL_USER:-root}"
export MYSQL_PASSWORD="${MYSQL_PASSWORD:-${MARIADB_ROOT_PASSWORD:-}}"
export MYSQL_DATABASE="${MYSQL_DATABASE:-${MARIADB_DATABASE:-}}"
if [ -z "${BKN_SAMPLE_VERSION:-}" ] && [ -f /opt/bkn-samples/VERSION ]; then
  BKN_SAMPLE_VERSION="$(tr -d '[:space:]' < /opt/bkn-samples/VERSION)"
  export BKN_SAMPLE_VERSION
fi
exec "${sample_dir}/db/init.sh"
