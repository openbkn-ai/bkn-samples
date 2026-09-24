#!/usr/bin/env python3
"""Run the supply-chain platform hook from BKN_SAMPLE_INPUT. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

SAMPLE_DIR = Path(__file__).resolve().parents[1]
TOOLS = SAMPLE_DIR / "tools"
KN_ID = "supply_ontology_hand"


def load_input() -> dict:
    path = os.environ.get("BKN_SAMPLE_INPUT", "")
    if not path:
        raise SystemExit("missing BKN_SAMPLE_INPUT")
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("sample") != "supply-chain":
        raise SystemExit("platform/install.sh only installs supply-chain")
    return payload


def build_config(payload: dict) -> dict:
    database = payload["database"]
    return {
        "openbkn": {"kn_id": KN_ID, "kn_name": payload["knowledgeNetwork"]["displayName"]},
        "database": {
            "engine": "mysql",
            "host": database["host"],
            "port": int(database["port"]),
            "database": database["name"],
            "user": database["user"],
            "password": database["password"],
        },
        "vega": {
            "catalog_id": payload["catalog"]["id"],
            "catalog_name": payload["catalog"]["name"],
            "catalog_host": database["host"],
            "connector_type": "mysql",
        },
    }


def commands(config_path: Path) -> list[list[str]]:
    python = sys.executable
    return [
        [python, str(TOOLS / "import_kn.py")],
        [python, str(TOOLS / "setup_catalog.py"), "--config", str(config_path)],
        [python, str(TOOLS / "bind_kn_resources.py"), "--config", str(config_path)],
        [python, str(TOOLS / "register_native_function_toolbox.py"), "--apply"],
        [python, str(TOOLS / "register_skills.py"), "--apply"],
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
        "degrade": [],
        "message": message,
    }
    Path(path).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    payload = load_input()
    config = build_config(payload)
    config_path = Path(os.environ.get("BKN_SAMPLE_CONFIG", "")) if os.environ.get("BKN_SAMPLE_CONFIG") else None
    if config_path is None:
        config_path = SAMPLE_DIR / "platform" / ".config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    if os.environ.get("BKN_SAMPLE_PRINT_ONLY") == "1":
        print(json.dumps(commands(config_path), ensure_ascii=False))
        write_output(payload, True)
        return 0
    for argv in commands(config_path):
        result = subprocess.run(argv, check=False)
        if result.returncode != 0:
            write_output(payload, False, f"{Path(argv[1]).name} failed")
            return result.returncode
    write_output(payload, True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
