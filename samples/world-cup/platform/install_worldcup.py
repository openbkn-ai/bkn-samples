#!/usr/bin/env python3
"""Run the existing world-cup platform steps from BKN_SAMPLE_INPUT. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parents[1]
KN_ID = "worldcup_vega_catalog_bkn"


def load_input() -> dict:
    path = os.environ.get("BKN_SAMPLE_INPUT", "")
    if not path:
        raise SystemExit("missing BKN_SAMPLE_INPUT")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("sample") != "world-cup":
        raise SystemExit("platform/install.sh only installs world-cup")
    return payload


def embedding_enabled() -> bool:
    if os.environ.get("BKN_SAMPLE_EMBEDDING", "1") == "0":
        return False
    return bool(os.environ.get("EMBEDDING_MODEL_NAME", "").strip())


def degrade_notes() -> list[dict]:
    if embedding_enabled():
        return []
    return [
        {
            "code": "keyword-index",
            "message": "No embedding model is configured. Indexes use keyword search only.",
        }
    ]


def write_output(payload: dict, ok: bool, message: str = "") -> None:
    path = os.environ.get("BKN_SAMPLE_OUTPUT", "")
    if not path:
        return
    body = {
        "ok": ok,
        "stage": "platform-install",
        "resources": {
            "catalogId": payload["catalog"]["id"],
            "knowledgeNetworkId": KN_ID,
        },
        "checks": [],
        "degrade": degrade_notes(),
        "message": message,
    }
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_env(payload: dict) -> dict:
    database = payload["database"]
    env = os.environ.copy()
    env.update(
        {
            "DB_HOST": str(database["host"]),
            "DB_PORT": str(database["port"]),
            "DB_NAME": str(database["name"]),
            "DB_USER": str(database["user"]),
            "DB_PASS": str(database["password"]),
            "VEGA_CATALOG_ID": str(payload["catalog"]["id"]),
            "VEGA_CATALOG_NAME": str(payload["catalog"]["name"]),
            "VEGA_SKIP_CREATE": "1",
            "SKIP_DOWNLOAD": "1",
            "SKIP_IMPORT": "1",
        }
    )
    if not embedding_enabled():
        env["EMBEDDING_MODEL_NAME"] = ""
    return env


def main() -> int:
    payload = load_input()
    if os.environ.get("BKN_SAMPLE_PRINT_ONLY") == "1":
        print(json.dumps(["./run.sh", "--from", "4"], ensure_ascii=False))
        write_output(payload, True)
        return 0
    result = subprocess.run(["./run.sh", "--from", "4"], cwd=SAMPLE_DIR, env=command_env(payload), check=False)
    if result.returncode != 0:
        write_output(payload, False, "run.sh failed")
        return result.returncode
    write_output(payload, True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
