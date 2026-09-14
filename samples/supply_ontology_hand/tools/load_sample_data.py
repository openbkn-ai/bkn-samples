from __future__ import annotations

import argparse
import csv
import getpass
import re
import re
import sys
from pathlib import Path
from typing import Iterable

import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import psycopg
from psycopg import sql as psycopg_sql

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_SAMPLE_ROWS = 200
_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_MAP = _SCRIPT_DIR / "mapping" / "object_table_map.yaml"
_COLUMN_TYPES = _SCRIPT_DIR / "mapping" / "column_types.yaml"

_SQLITE_TYPE_MAP = {
    "BIGINT": "INTEGER",
    "FLOAT": "REAL",
    "DECIMAL": "NUMERIC",
    "TIMESTAMP": "TEXT",
    "TEXT": "TEXT",
}

_POSTGRES_TYPE_MAP = {
    "BIGINT": "BIGINT",
    "FLOAT": "DOUBLE PRECISION",
    "DECIMAL": "DECIMAL(18,6)",
    "TIMESTAMP": "TIMESTAMP",
    "TEXT": "TEXT",
}

_MYSQL_TYPE_MAP = {
    "BIGINT": "BIGINT",
    "FLOAT": "DOUBLE",
    "DECIMAL": "DECIMAL(18,6)",
    "TIMESTAMP": "DATETIME",
    "TEXT": "TEXT",
}


def _load_column_overrides() -> dict:
    if not _COLUMN_TYPES.is_file():
        return {}
    return yaml.safe_load(_COLUMN_TYPES.read_text(encoding="utf-8")) or {}


def column_schema(table: str, column: str, values: Iterable[str], engine_name: str) -> tuple[str, str]:
    """Resolve a column from business schema first, inference only as fallback."""
    spec = _load_column_overrides().get("overrides", {}).get(table, {}).get(column)
    if spec:
        kind = str(spec["type"]).upper()
        if kind == "VARCHAR":
            return column, f"VARCHAR({int(spec['length'])})"
        if kind == "DECIMAL":
            return column, f"DECIMAL({int(spec['precision'])},{int(spec['scale'])})"
        return column, sql_type_for(kind, engine_name)
    return column, sql_type_for(infer_column_type(values), engine_name)


def infer_column_type(values: Iterable[str]) -> str:
    samples = [v.strip() for v in values if v is not None and str(v).strip() != ""]
    if not samples:
        return "TEXT"
    if all(re.fullmatch(r"-?\d+", s) for s in samples):
        return "BIGINT"
    if all(re.fullmatch(r"-?\d+(\.\d+)?", s) for s in samples):
        return "FLOAT"
    if all(_DATE_RE.match(s) for s in samples):
        return "TIMESTAMP"
    return "TEXT"


def resolve_load_order(mapping: dict) -> list[str]:
    return list(mapping["load_order"])


def sql_type_for(logical: str, engine_name: str) -> str:
    if engine_name == "sqlite":
        return _SQLITE_TYPE_MAP.get(logical, "TEXT")
    if engine_name == "mysql":
        return _MYSQL_TYPE_MAP.get(logical, "TEXT")
    return _POSTGRES_TYPE_MAP.get(logical, "TEXT")


def quote_ident(name: str, engine_name: str) -> str:
    if engine_name == "mysql":
        return f"`{name}`"
    return f'"{name}"'


def build_engine(db: dict) -> Engine:
    eng = db["engine"]
    if eng == "postgres":
        url = (
            f"postgresql+psycopg://{db['user']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['database']}"
        )
    elif eng == "mysql":
        url = (
            f"mysql+pymysql://{db['user']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['database']}?charset=utf8mb4"
        )
    elif eng == "sqlite":
        db_path = db.get("database", ":memory:")
        url = f"sqlite:///{db_path}"
    else:
        raise ValueError(f"unsupported engine: {eng}")
    return create_engine(url)


def ensure_postgres_database(db: dict) -> None:
    name = str(db["database"])
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("database name must contain only letters, digits, and underscores")
    maintenance = dict(db)
    maintenance["database"] = "postgres"
    conn = psycopg.connect(
        host=maintenance["host"], port=maintenance["port"],
        dbname=maintenance["database"], user=maintenance["user"],
        password=maintenance["password"], autocommit=True,
    )
    try:
        exists = conn.execute("select 1 from pg_database where datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(psycopg_sql.SQL("CREATE DATABASE {}" ).format(psycopg_sql.Identifier(name)))
            print(f"Created database: {name}")
        else:
            print(f"Database already exists: {name}")
    finally:
        conn.close()


def _infer_schema(table: str, header: list[str], rows: list[list[str]], engine_name: str) -> list[tuple[str, str]]:
    col_types: list[tuple[str, str]] = []
    for idx, col in enumerate(header):
        samples = (row[idx] if idx < len(row) else "" for row in rows[:_SAMPLE_ROWS])
        col_types.append(column_schema(table, col, samples, engine_name))
    return col_types


def _normalize_row(row: list[str], num_cols: int) -> tuple:
    out: list[str | None] = []
    for i in range(num_cols):
        val = row[i] if i < len(row) else ""
        if val is None or str(val).strip() == "":
            out.append(None)
        else:
            out.append(val)
    return tuple(out)


def _batch_insert(conn, insert_sql: str, rows: list[list[str]], num_cols: int) -> None:
    if not rows:
        return
    tuples = [_normalize_row(row, num_cols) for row in rows]
    raw_conn = conn.connection.dbapi_connection
    cursor = raw_conn.cursor()
    cursor.executemany(insert_sql, tuples)
    cursor.close()


def _load_table(
    engine: Engine,
    table: str,
    csv_path: Path,
    mode: str,
    engine_name: str,
) -> int:
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        sample_rows: list[list[str]] = []
        all_rows: list[list[str]] = []
        for row in reader:
            if len(sample_rows) < _SAMPLE_ROWS:
                sample_rows.append(row)
            all_rows.append(row)

    schema = _infer_schema(table, header, sample_rows, engine_name)
    q_table = quote_ident(table, engine_name)
    col_defs = ", ".join(
        f"{quote_ident(col, engine_name)} {sql_type}" for col, sql_type in schema
    )
    col_names = ", ".join(quote_ident(col, engine_name) for col, _ in schema)
    placeholders = ", ".join("?" if engine_name == "sqlite" else "%s" for _ in schema)

    with engine.begin() as conn:
        if mode == "recreate":
            conn.execute(text(f"DROP TABLE IF EXISTS {q_table}"))
            conn.execute(text(f"CREATE TABLE {q_table} ({col_defs})"))
        elif mode != "append_if_empty":
            raise ValueError(f"unsupported load mode: {mode}")

        if all_rows:
            insert_sql = f"INSERT INTO {q_table} ({col_names}) VALUES ({placeholders})"
            _batch_insert(conn, insert_sql, all_rows, len(header))

    count = len(all_rows)
    print(f"{table}: {count} rows")
    return count


def load_all(engine: Engine, cfg: dict, mapping: dict, *, table_prefix: str = "") -> dict[str, int]:
    load_cfg = cfg["load"]
    sample_dir = Path(load_cfg["sample_dir"])
    mode = load_cfg.get("mode", "recreate")
    on_error = load_cfg.get("on_error", "stop")
    engine_name = cfg["database"]["engine"]

    report: dict[str, int] = {}
    for table in resolve_load_order(mapping):
        csv_path = sample_dir / f"{table}.csv"
        try:
            report[table_prefix + table] = _load_table(
                engine, table_prefix + table, csv_path, mode, engine_name
            )
        except Exception as exc:
            print(f"ERROR loading {table}: {exc}", file=sys.stderr)
            if on_error == "stop":
                raise
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load data/*.csv into a database")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--interactive", action="store_true", help="Prompt for PostgreSQL connection details without saving them")
    parser.add_argument("--table-prefix", default=None, help="Prefix for destination table names, e.g. hand_")
    parser.add_argument("--create-database", action="store_true", help="Create the target PostgreSQL database using the postgres maintenance database")
    args = parser.parse_args(argv)

    if args.interactive:
        cfg = {
            "database": {
                "engine": "postgres",
                "host": input("数据库 Host: ").strip(),
                "port": int(input("端口 [5432]: ") or "5432"),
                "database": input("数据库名（必填）: ").strip(),
                "user": input("用户名: ").strip(),
                "password": getpass.getpass("密码（输入时不显示）: "),
            },
            "load": {
                "sample_dir": str(_SCRIPT_DIR.parent / "data"),
                "mode": "recreate",
                "on_error": "stop",
            },
        }
    else:
        config_path = Path(args.config)
        if not config_path.is_file():
            print(f"Config not found: {config_path}", file=sys.stderr)
            return 1
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not cfg["database"]["database"]:
        print("数据库名不能为空；请填写本环境 sample 数据库名", file=sys.stderr)
        return 1
    mapping = yaml.safe_load(_DEFAULT_MAP.read_text(encoding="utf-8"))
    table_prefix = args.table_prefix
    if table_prefix is None:
        table_prefix = (cfg.get("load") or {}).get("table_prefix", "")

    try:
        engine = build_engine(cfg["database"])
        if args.create_database:
            ensure_postgres_database(cfg["database"])
            engine = build_engine(cfg["database"])
        with engine.connect():
            pass
        print("Database connection succeeded.")
        if args.interactive:
            answer = input(f"导入 {len(mapping['load_order'])} 张表并加前缀 {table_prefix!r}？输入 yes 开始：").strip().lower()
            if answer not in ("yes", "y"):
                print("已取消，没有写入数据。")
                return 0
        report = load_all(engine, cfg, mapping, table_prefix=table_prefix)
    except Exception as exc:
        print(f"Load failed: {exc}", file=sys.stderr)
        if cfg.get("load", {}).get("on_error", "stop") == "stop":
            return 1
        return 1

    total = sum(report.values())
    print(f"Done. {len(report)} tables, {total} rows total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
