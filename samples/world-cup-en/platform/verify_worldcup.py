#!/usr/bin/env python3
"""Smoke-check the world-cup-en platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess
import re
import sys
from pathlib import Path


DATA_CHECKS = ("tables-discovered", "cross-table-query")
KN_ID = "worldcup_en"
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


def model_ready(run_cli) -> bool:
    for directory, command in (("object_types", "object-type"), ("relation_types", "relation-type"), ("concept_groups", "concept-group")):
        expected = {re.search(r"^id: (.+)$", path.read_text(), re.M).group(1)
                    for path in (SAMPLE_DIR / "kn" / directory).glob("*.bkn")}
        result = run_cli(["bkn", command, "list", KN_ID])
        entries = result if isinstance(result, list) else result.get("entries", [])
        if {entry.get("id") for entry in entries} != expected:
            return False
    return True


def build_checks(*, data_ok: bool, model_ok: bool) -> list[dict]:
    return [{"name": name, "ok": data_ok} for name in DATA_CHECKS] + [{"name": "model-imported", "ok": model_ok}]


def _openbkn(args: list[str]) -> dict:
    completed = subprocess.run(["openbkn", "--json", *args], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError("openbkn command failed")
    payload = json.loads(completed.stdout or "{}")
    if not isinstance(payload, (dict, list)):
        raise RuntimeError("openbkn command failed")
    return payload


def main() -> int:
    raw = json.loads(Path(os.environ["BKN_SAMPLE_INPUT"]).read_text(encoding="utf-8"))
    if raw.get("sample") != "world-cup-en":
        print("unexpected sample", file=sys.stderr)
        return 1
    apply_database_env(raw)
    if os.environ.get("BKN_SAMPLE_PRINT_ONLY") == "1":
        data_ok = True
        model_ok = True
    else:
        sys.path.insert(0, str(SAMPLE_DIR))
        from db.verify_worldcup import main as verify_database

        data_ok = verify_database() == 0
        model_ok = model_ready(_openbkn)
    checks = build_checks(data_ok=data_ok, model_ok=model_ok)
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
        "message": "" if passed else "world-cup-en verification failed",
    }
    output = os.environ.get("BKN_SAMPLE_OUTPUT", "")
    if output:
        Path(output).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
