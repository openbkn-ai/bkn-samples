#!/usr/bin/env python3
"""Smoke-check the world-cup platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess

try:
    from installer.sample_logging import run as run_sample_command
except ImportError:
    # Older installers retain the original subprocess behavior.
    run_sample_command = subprocess.run
import sys
from pathlib import Path

import yaml

DATA_CHECKS = ("tables-discovered", "cross-table-query")
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


def skills_ready(run_cli) -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from ownership_receipt import read
    from register_skills import local_skills

    listed = _entries(run_cli(["skill", "list", "--all"]), "data", "entries")
    owned = set(read()["skills"]) if os.environ.get("BKN_SAMPLE_RECEIPT") else None
    for name, _ in local_skills():
        matches = [item for item in listed if item.get("name") == name]
        if len(matches) != 1 or matches[0].get("status") != "published":
            return False
        if owned is not None and (matches[0].get("skill_id") or matches[0].get("id")) not in owned:
            return False
    return True


def build_checks(*, data_ok: bool, tool_ok: bool | None) -> list[dict]:
    checks = [{"name": name, "ok": data_ok} for name in DATA_CHECKS]
    if tool_ok is not None:
        checks.append({"name": "skills-published", "ok": tool_ok})
    return checks


def _openbkn(args: list[str]) -> dict:
    completed = run_sample_command(["openbkn", "--json", *args], check=False, capture_output=True, text=True)
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
        document = yaml.safe_load((SAMPLE_DIR / "sample.yaml").read_text(encoding="utf-8"))
        tool_ok = skills_ready(_openbkn) if document["spec"]["components"].get("skills") else None
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
