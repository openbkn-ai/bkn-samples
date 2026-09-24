#!/usr/bin/env python3
"""Load the supply-chain CSVs into MariaDB and record bkn_sample_meta."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import yaml
from sqlalchemy import create_engine, text

SAMPLE_DIR = Path(__file__).resolve().parents[1]
TOOLS_DIR = SAMPLE_DIR / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from load_sample_data import load_all, resolve_load_order  # noqa: E402

EXPECTED_SAMPLE = "supply-chain"
ROW_COUNTS = Path(__file__).resolve().parent / "row_counts.json"


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing {name}")
    return value


def _version() -> str:
    candidates = [
        os.environ.get("BKN_SAMPLE_VERSION", "").strip(),
        Path("/opt/bkn-samples/VERSION").read_text(encoding="utf-8").strip()
        if Path("/opt/bkn-samples/VERSION").is_file()
        else "",
    ]
    repo_version = SAMPLE_DIR.parents[2] / "VERSION"
    if repo_version.is_file():
        candidates.append(repo_version.read_text(encoding="utf-8").strip())
    for item in candidates:
        if item:
            return item
    raise SystemExit("sample version not found")


def _data_version() -> str:
    payload = ROW_COUNTS.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def _engine(database: str):
    user = quote_plus(_env("MYSQL_USER"))
    password = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))
    socket_path = os.environ.get("MYSQL_UNIX_SOCKET", "").strip()
    if socket_path:
        url = (
            f"mysql+pymysql://{user}:{password}@localhost/{database}"
            f"?charset=utf8mb4&unix_socket={quote_plus(socket_path)}"
        )
    else:
        host = _env("MYSQL_HOST")
        port = os.environ.get("MYSQL_PORT", "3306")
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    return create_engine(url)


def _admin_database() -> str:
    return os.environ.get("MYSQL_ADMIN_DATABASE", "mysql")


def _counts() -> dict[str, int]:
    raw = json.loads(ROW_COUNTS.read_text(encoding="utf-8"))
    return {name: int(count) for name, count in raw.items()}


def _ready(database: str, version: str) -> bool:
    engine = _engine(_admin_database())
    with engine.connect() as conn:
        exists = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = :db AND table_name = 'bkn_sample_meta'"
            ),
            {"db": database},
        ).scalar()
        if not exists:
            engine.dispose()
            return False
        row = conn.execute(
            text(
                f"SELECT status, sample_version FROM `{database}`.bkn_sample_meta "
                "WHERE sample_id = :sample"
            ),
            {"sample": EXPECTED_SAMPLE},
        ).first()
    engine.dispose()
    return bool(row and row[0] == "ready" and row[1] == version)


def _create_database(name: str) -> None:
    admin = _engine(_admin_database())
    with admin.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4"))
    admin.dispose()


def _drop_database(name: str) -> None:
    admin = _engine(_admin_database())
    with admin.begin() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS `{name}`"))
    admin.dispose()


def _write_meta(database: str, version: str) -> None:
    engine = _engine(database)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS bkn_sample_meta ("
                " sample_id VARCHAR(64) NOT NULL PRIMARY KEY,"
                " sample_version VARCHAR(32) NOT NULL,"
                " data_version CHAR(64) NOT NULL,"
                " status VARCHAR(16) NOT NULL,"
                " finished_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            text(
                "REPLACE INTO bkn_sample_meta "
                "(sample_id, sample_version, data_version, status) "
                "VALUES (:sample, :version, :data_version, 'ready')"
            ),
            {
                "sample": EXPECTED_SAMPLE,
                "version": version,
                "data_version": _data_version(),
            },
        )
    engine.dispose()


def load_supply() -> None:
    sample_id = _env("BKN_SAMPLE_ID")
    if sample_id != EXPECTED_SAMPLE:
        raise SystemExit(f"db/init.sh only loads {EXPECTED_SAMPLE}, got {sample_id}")
    database = _env("MYSQL_DATABASE")
    version = _version()
    _create_database(database)
    if _ready(database, version):
        print(f"{database} already ready at {version}")
        return

    loading = f"{database}_loading"
    _drop_database(loading)
    _create_database(loading)
    mapping = yaml.safe_load((TOOLS_DIR / "mapping" / "object_table_map.yaml").read_text(encoding="utf-8"))
    cfg = {
        "database": {"engine": "mysql"},
        "load": {"sample_dir": str(SAMPLE_DIR / "data"), "mode": "recreate", "on_error": "stop"},
    }
    report = load_all(_engine(loading), cfg, mapping)
    expected = _counts()
    if report != expected:
        _drop_database(loading)
        raise SystemExit(f"row counts do not match the published list: {report}")
    _create_database(database)
    admin = _engine(_admin_database())
    tables = resolve_load_order(mapping)
    with admin.begin() as conn:
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS `{database}`.`{table}`"))
        renames = ", ".join(f"`{loading}`.`{table}` TO `{database}`.`{table}`" for table in tables)
        conn.execute(text(f"RENAME TABLE {renames}"))
    admin.dispose()
    _drop_database(loading)
    _write_meta(database, version)
    print(f"loaded {len(report)} tables into {database}")


if __name__ == "__main__":
    load_supply()
