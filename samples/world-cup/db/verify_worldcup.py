#!/usr/bin/env python3
"""Confirm the world-cup MariaDB load is ready and the representative join returns rows."""

from __future__ import annotations

import os
import sys
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

EXPECTED_SAMPLE = "world-cup"
EXPECTED_TABLES = 27


def main() -> int:
    if os.environ.get("BKN_SAMPLE_ID", "").strip() not in ("", EXPECTED_SAMPLE):
        print("unexpected BKN_SAMPLE_ID", file=sys.stderr)
        return 1
    user = quote_plus(os.environ["MYSQL_USER"])
    password = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))
    database = os.environ["MYSQL_DATABASE"]
    socket_path = os.environ.get("MYSQL_UNIX_SOCKET", "").strip()
    if socket_path:
        url = (
            f"mysql+pymysql://{user}:{password}@localhost/{database}"
            f"?charset=utf8mb4&unix_socket={quote_plus(socket_path)}"
        )
    else:
        host = os.environ["MYSQL_HOST"]
        port = os.environ.get("MYSQL_PORT", "3306")
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    engine = create_engine(url)
    version = os.environ.get("BKN_SAMPLE_VERSION", "").strip()
    with engine.connect() as conn:
        found = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = :db AND table_name LIKE 'wc\\_%'"
            ),
            {"db": database},
        ).scalar()
        meta = conn.execute(
            text("SELECT status, sample_version FROM bkn_sample_meta WHERE sample_id = :sample"),
            {"sample": EXPECTED_SAMPLE},
        ).first()
        join_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM wc_matches m "
                "JOIN wc_teams t ON m.home_team_id = t.team_id"
            )
        ).scalar()
    if int(found) != EXPECTED_TABLES:
        print(f"expected {EXPECTED_TABLES} wc_ tables, found {found}", file=sys.stderr)
        return 1
    if meta is None or meta[0] != "ready":
        print("bkn_sample_meta is not ready", file=sys.stderr)
        return 1
    if version and meta[1] != version:
        print(f"sample version {meta[1]} != {version}", file=sys.stderr)
        return 1
    if int(join_count) <= 0:
        print("wc_matches did not join wc_teams", file=sys.stderr)
        return 1
    print(f"verified {EXPECTED_TABLES} tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
