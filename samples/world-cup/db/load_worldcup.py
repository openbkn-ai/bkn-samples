#!/usr/bin/env python3
"""Download the locked world-cup CSVs and switch them into MariaDB."""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

import yaml

SAMPLE_DIR = Path(__file__).resolve().parents[1]
LOCK_PATH = SAMPLE_DIR / "dataset.lock"
EXPECTED_SAMPLE = "world-cup"
WIDE_TABLES = frozenset({"wc_matches", "wc_team_appearances"})
EXPECTED_FILES = 27


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
    repo_version = SAMPLE_DIR.parents[1] / "VERSION"
    if repo_version.is_file():
        candidates.append(repo_version.read_text(encoding="utf-8").strip())
    for item in candidates:
        if item:
            return item
    raise SystemExit("sample version not found")


def read_lock(path: Path = LOCK_PATH) -> dict:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    files = document.get("files") or []
    if len(files) != EXPECTED_FILES:
        raise SystemExit(f"dataset.lock must list {EXPECTED_FILES} files")
    source = document.get("source") or {}
    if not source.get("commit") or not source.get("baseUrl"):
        raise SystemExit("dataset.lock source is incomplete")
    return document


def cache_dir() -> Path:
    configured = os.environ.get("BKN_SAMPLE_CACHE", "").strip()
    if configured:
        return Path(configured)
    return Path("/var/lib/bkn-samples/cache/world-cup")


def fetch_locked_files(lock: dict, destination: Path, opener=urllib.request.urlopen) -> list[Path]:
    """Download every locked file. A failed download or checksum leaves no renamed database."""
    destination.mkdir(parents=True, exist_ok=True)
    base = str(lock["source"]["baseUrl"]).rstrip("/")
    saved: list[Path] = []
    for item in lock["files"]:
        name = item["path"]
        expected = item["sha256"]
        target = destination / name
        if target.is_file() and _sha256(target) == expected:
            saved.append(target)
            continue
        partial = target.with_suffix(target.suffix + ".part")
        partial.unlink(missing_ok=True)
        try:
            with opener(f"{base}/{name}", timeout=60) as response, partial.open("wb") as handle:
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
        except Exception:
            partial.unlink(missing_ok=True)
            raise SystemExit(f"sample data unavailable: {name}") from None
        if _sha256(partial) != expected:
            partial.unlink(missing_ok=True)
            raise SystemExit(f"checksum mismatch: {name}")
        partial.replace(target)
        saved.append(target)
    return saved


def table_name(csv_path: Path) -> str:
    stem = "".join(char if char.isalnum() or char == "_" else "_" for char in csv_path.stem)
    return f"wc_{stem}"


def create_table_sql(table: str, columns: list[str]) -> str:
    width = 255 if table in WIDE_TABLES else 512
    quoted = ", ".join(f"`{column.replace('`', '``')}` VARCHAR({width})" for column in columns)
    return (
        f"DROP TABLE IF EXISTS `{table}`; "
        f"CREATE TABLE `{table}` ({quoted}) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _engine(database: str):
    from urllib.parse import quote_plus

    from sqlalchemy import create_engine

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


def _create_database(name: str) -> None:
    from sqlalchemy import text

    admin = _engine(_admin_database())
    with admin.begin() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4"))
    admin.dispose()


def _drop_database(name: str) -> None:
    from sqlalchemy import text

    admin = _engine(_admin_database())
    with admin.begin() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS `{name}`"))
    admin.dispose()


def _ready(database: str, version: str) -> bool:
    from sqlalchemy import text

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


def _load_csvs(database: str, files: list[Path]) -> list[str]:
    import csv

    from sqlalchemy import text

    engine = _engine(database)
    tables: list[str] = []
    with engine.begin() as conn:
        for path in files:
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))
            if not rows:
                continue
            header, data = rows[0], rows[1:]
            table = table_name(path)
            conn.execute(text(create_table_sql(table, header)))
            if data:
                columns = ", ".join(f"`{column.replace('`', '``')}`" for column in header)
                placeholders = ", ".join(f":c{index}" for index in range(len(header)))
                statement = text(f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})")
                conn.execute(
                    statement,
                    [{f"c{index}": value or None for index, value in enumerate(row + [""] * len(header))} for row in (record[: len(header)] for record in data)],
                )
            tables.append(table)
    engine.dispose()
    return tables


def _promote(database: str, loading: str, tables: list[str]) -> None:
    from sqlalchemy import text

    admin = _engine(_admin_database())
    with admin.begin() as conn:
        for table in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS `{database}`.`{table}`"))
        renames = ", ".join(f"`{loading}`.`{table}` TO `{database}`.`{table}`" for table in tables)
        conn.execute(text(f"RENAME TABLE {renames}"))
    admin.dispose()


def _write_meta(database: str, version: str, data_version: str) -> None:
    from sqlalchemy import text

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
            {"sample": EXPECTED_SAMPLE, "version": version, "data_version": data_version},
        )
    engine.dispose()


def load_worldcup(opener=urllib.request.urlopen) -> None:
    sample_id = _env("BKN_SAMPLE_ID")
    if sample_id != EXPECTED_SAMPLE:
        raise SystemExit(f"db/init.sh only loads {EXPECTED_SAMPLE}, got {sample_id}")
    database = _env("MYSQL_DATABASE")
    version = _version()
    lock = read_lock()
    try:
        files = fetch_locked_files(lock, cache_dir(), opener)
    except SystemExit:
        raise
    _create_database(database)
    if _ready(database, version):
        print(f"{database} already ready at {version}")
        return
    loading = f"{database}_loading"
    _drop_database(loading)
    _create_database(loading)
    try:
        tables = _load_csvs(loading, files)
        if len(tables) != EXPECTED_FILES:
            raise SystemExit(f"loaded {len(tables)} tables, expected {EXPECTED_FILES}")
        _promote(database, loading, tables)
    except BaseException:
        _drop_database(loading)
        raise
    _drop_database(loading)
    _write_meta(database, version, str(lock["source"]["commit"]))
    print(f"loaded {len(tables)} tables into {database}")


if __name__ == "__main__":
    load_worldcup()
