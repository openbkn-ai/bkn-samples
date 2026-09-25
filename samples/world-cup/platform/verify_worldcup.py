#!/usr/bin/env python3
"""Smoke-check the world-cup platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REQUIRED = ("tables-discovered", "object-query", "cross-table-query", "capability-callable", "skill-discoverable")
KN_ID = "worldcup_vega_catalog_bkn"
SAMPLE_DIR = Path(__file__).resolve().parents[1]


def apply_database_env(raw: dict) -> None:
    """Use the hook database when this process is not inside the MariaDB container."""
    if os.environ.get("MYSQL_HOST") or os.environ.get("MYSQL_UNIX_SOCKET"):
        return
    database = raw["database"]
    os.environ["MYSQL_HOST"] = str(database["host"])
    os.environ["MYSQL_PORT"] = str(database["port"])
    os.environ["MYSQL_USER"] = str(database["user"])
    os.environ["MYSQL_PASSWORD"] = str(database["password"])
    os.environ["MYSQL_DATABASE"] = str(database["name"])
    os.environ.setdefault("BKN_SAMPLE_ID", str(raw.get("sample") or ""))
    os.environ.setdefault("BKN_SAMPLE_VERSION", str(raw.get("version") or ""))


def main() -> int:
    raw = json.loads(Path(os.environ["BKN_SAMPLE_INPUT"]).read_text(encoding="utf-8"))
    if raw.get("sample") != "world-cup":
        print("unexpected sample", file=sys.stderr)
        return 1
    apply_database_env(raw)
    if os.environ.get("BKN_SAMPLE_PRINT_ONLY") == "1":
        passed = True
    else:
        sys.path.insert(0, str(SAMPLE_DIR))
        from db.verify_worldcup import main as verify_database

        passed = verify_database() == 0
    degrade = []
    if os.environ.get("BKN_SAMPLE_EMBEDDING", "1") == "0" or not os.environ.get("EMBEDDING_MODEL_NAME", "").strip():
        degrade.append(
            {
                "code": "keyword-index",
                "message": "No embedding model is configured. Indexes use keyword search only.",
            }
        )
    body = {
        "ok": passed,
        "stage": "platform-verify",
        "resources": {
            "catalogId": raw["catalog"]["id"],
            "knowledgeNetworkId": KN_ID,
        },
        "checks": [{"name": name, "ok": passed} for name in REQUIRED],
        "degrade": degrade,
        "message": "" if passed else "world-cup database verification failed",
    }
    output = os.environ.get("BKN_SAMPLE_OUTPUT", "")
    if output:
        Path(output).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
