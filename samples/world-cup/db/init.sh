#!/usr/bin/env bash
set -Eeuo pipefail

root=/opt/bkn-samples
lock="$root/samples/world-cup/dataset.lock"
cache=/var/lib/bkn-samples/cache/world-cup
mkdir -p "$cache"

python3 - "$lock" "$cache" <<'PY'
import hashlib
import pathlib
import sys
import urllib.request
import yaml

lock = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
cache = pathlib.Path(sys.argv[2])
base = lock["source"]["baseUrl"].rstrip("/")
for item in lock["files"]:
    name, expected = item["path"], item["sha256"]
    target = cache / name
    def valid(path):
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected
    if valid(target):
        print(f"cached: {name}")
        continue
    part = target.with_suffix(target.suffix + ".part")
    part.unlink(missing_ok=True)
    print(f"download: {name}")
    try:
        with urllib.request.urlopen(f"{base}/{name}", timeout=60) as response, part.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
    except Exception:
        part.unlink(missing_ok=True)
        raise
    if not valid(part):
        part.unlink(missing_ok=True)
        raise SystemExit(f"checksum mismatch: {name}")
    part.replace(target)
PY

python3 - "$cache" <<'PY' | MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot "$BKN_DATABASE" --default-character-set=utf8mb4
import csv
import pathlib
import re
import sys

cache = pathlib.Path(sys.argv[1])
def quote(value):
    if value == "":
        return "NULL"
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
for path in sorted(cache.glob("*.csv")):
    table = "wc_" + re.sub(r"[^0-9A-Za-z_]", "_", path.stem)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = csv.reader(handle)
        header = next(rows)
        columns = ", ".join("`" + column.replace("`", "``") + "` VARCHAR(255)" for column in header)
        print(f"DROP TABLE IF EXISTS `{table}`;")
        print(f"CREATE TABLE `{table}` ({columns}) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4;")
        for row in rows:
            row = (row + [""] * len(header))[:len(header)]
            print(f"INSERT INTO `{table}` VALUES ({', '.join(quote(value) for value in row)});")
PY

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
VALUES ('world-cup', '1.0.0', '1.0.0', 'ready');
SQL
