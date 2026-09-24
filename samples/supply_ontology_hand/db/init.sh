#!/usr/bin/env bash
set -Eeuo pipefail

root=/opt/bkn-samples
config=/tmp/supply-sample-config.yaml

cat >"$config" <<EOF
database:
  engine: mysql
  host: localhost
  port: 3306
  unix_socket: /run/mysqld/mysqld.sock
  database: ${BKN_DATABASE}
  user: bkn_sample
  password: ${MARIADB_PASSWORD}
load:
  sample_dir: ${root}/samples/supply_ontology_hand/data
  mode: recreate
  on_error: stop
EOF

python3 "$root/samples/supply_ontology_hand/tools/load_sample_data.py" --config "$config"
mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" "$BKN_DATABASE" <<'SQL'
CREATE TABLE IF NOT EXISTS bkn_sample_meta (
  sample_id VARCHAR(128) NOT NULL,
  sample_version VARCHAR(64) NOT NULL,
  data_version VARCHAR(64) NOT NULL,
  status VARCHAR(16) NOT NULL,
  completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
DELETE FROM bkn_sample_meta;
INSERT INTO bkn_sample_meta (sample_id, sample_version, data_version, status)
VALUES ('supply-chain', '1.0.0', '1.0.0', 'ready');
SQL
rm -f "$config"
