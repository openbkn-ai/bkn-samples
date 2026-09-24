#!/usr/bin/env python3
"""Confirm the supply-chain MariaDB load matches the published row counts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

EXPECTED_SAMPLE = "supply-chain"
ROW_COUNTS = json.loads((Path(__file__).resolve().parent / "row_counts.json").read_text(encoding="utf-8"))


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
        for table, expected in ROW_COUNTS.items():
            found = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar()
            if int(found) != int(expected):
                print(f"{table}: expected {expected} rows, found {found}", file=sys.stderr)
                return 1
        meta = conn.execute(
            text(
                "SELECT status, sample_version FROM bkn_sample_meta "
                "WHERE sample_id = :sample"
            ),
            {"sample": EXPECTED_SAMPLE},
        ).first()
        join_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM sales_order s "
                "JOIN hd_product_view p ON s.product_code = p.material_code"
            )
        ).scalar()
    if meta is None or meta[0] != "ready":
        print("bkn_sample_meta is not ready", file=sys.stderr)
        return 1
    if version and meta[1] != version:
        print(f"sample version {meta[1]} != {version}", file=sys.stderr)
        return 1
    if int(join_count) <= 0:
        print("sales_order did not join hd_product_view", file=sys.stderr)
        return 1
    print(f"verified {len(ROW_COUNTS)} tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
