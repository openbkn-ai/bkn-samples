#!/bin/sh
# First-boot dispatcher. MariaDB runs this only when the data directory is empty.
set -eu
sample_id="${BKN_SAMPLE_ID:-}"
root="${BKN_SAMPLE_ROOT:-/opt/bkn-samples/samples}"
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
# The MariaDB entrypoint exports MYSQL_USER as the application user during first boot.
# Loading creates and renames databases, so it must run as root.
export MYSQL_USER=root
export MYSQL_PASSWORD="${MARIADB_ROOT_PASSWORD:-}"
export MYSQL_DATABASE="${MYSQL_DATABASE:-${MARIADB_DATABASE:-}}"
# Init runs as the mysql user. The default cache path is not writable by that user.
if [ "$sample_id" = "world-cup" ]; then
  cache_root="${TMPDIR:-/tmp}/bkn-samples/cache"
  mkdir -p "${cache_root}/${sample_id}"
  export BKN_SAMPLE_CACHE="${cache_root}/${sample_id}"
fi
if [ -z "${BKN_SAMPLE_VERSION:-}" ] && [ -f /opt/bkn-samples/VERSION ]; then
  BKN_SAMPLE_VERSION="$(tr -d '[:space:]' < /opt/bkn-samples/VERSION)"
  export BKN_SAMPLE_VERSION
fi
exec "${sample_dir}/db/init.sh"
