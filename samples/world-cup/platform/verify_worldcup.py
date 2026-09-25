#!/usr/bin/env python3
"""Smoke-check the world-cup platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

DATA_CHECKS = ("tables-discovered", "cross-table-query")
BOX_NAME = "wc_vega_query"
TOOL_NAME = "vega_sql_execute"
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


def _entries(payload: dict, *keys: str) -> list:
    for key in keys:
        inner = payload.get(key)
        if isinstance(inner, list):
            return inner
    return []


def tool_ready(run_cli) -> bool:
    listing = run_cli(["toolbox", "list", "--keyword", BOX_NAME, "--limit", "100"])
    box = next((item for item in _entries(listing, "data", "entries") if item.get("box_name") == BOX_NAME), None)
    if not box or not box.get("box_id"):
        return False
    tools = run_cli(["tool", "list", "--toolbox", box["box_id"], "--all"])
    return any(
        item.get("name") == TOOL_NAME and item.get("status") == "enabled"
        for item in _entries(tools, "tools", "data", "entries")
    )


def build_checks(*, data_ok: bool, tool_ok: bool) -> list[dict]:
    checks = [{"name": name, "ok": data_ok} for name in DATA_CHECKS]
    checks.append({"name": "capability-callable", "ok": tool_ok})
    return checks


def _openbkn(args: list[str]) -> dict:
    completed = subprocess.run(["openbkn", "--json", *args], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError("openbkn command failed")
    payload = json.loads(completed.stdout or "{}")
    if not isinstance(payload, dict):
        raise RuntimeError("openbkn command failed")
    return payload


def main() -> int:
    raw = json.loads(Path(os.environ["BKN_SAMPLE_INPUT"]).read_text(encoding="utf-8"))
    if raw.get("sample") != "world-cup":
        print("unexpected sample", file=sys.stderr)
        return 1
    apply_database_env(raw)
    if os.environ.get("BKN_SAMPLE_PRINT_ONLY") == "1":
        data_ok = True
        tool_ok = True
    else:
        sys.path.insert(0, str(SAMPLE_DIR))
        from db.verify_worldcup import main as verify_database

        data_ok = verify_database() == 0
        tool_ok = tool_ready(_openbkn)
    checks = build_checks(data_ok=data_ok, tool_ok=tool_ok)
    passed = all(item["ok"] for item in checks)
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
        "checks": checks,
        "degrade": degrade,
        "message": "" if passed else "world-cup verification failed",
    }
    output = os.environ.get("BKN_SAMPLE_OUTPUT", "")
    if output:
        Path(output).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
