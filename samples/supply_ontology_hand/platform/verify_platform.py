#!/usr/bin/env python3
"""Smoke-check the supply-chain platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REQUIRED = ("tables-discovered", "object-query", "cross-table-query", "capability-callable", "skill-discoverable")
DATA_CHECKS = ("tables-discovered", "object-query", "cross-table-query")
BOX_NAME = "供应链原生计算函数"
SAMPLE_DIR = Path(__file__).resolve().parents[1]


def _entries(payload: dict, *keys: str) -> list:
    for key in keys:
        inner = payload.get(key)
        if isinstance(inner, list):
            return inner
    return []


def capability_ready(run_cli) -> bool:
    listing = run_cli(["toolbox", "list", "--keyword", BOX_NAME, "--limit", "100"])
    box = next((item for item in _entries(listing, "data", "entries") if item.get("box_name") == BOX_NAME), None)
    if not box or not box.get("box_id"):
        return False
    tools = run_cli(["tool", "list", "--toolbox", box["box_id"], "--all"])
    return any(item.get("status") == "enabled" for item in _entries(tools, "tools", "data", "entries"))


def skills_ready(run_cli) -> bool:
    sys.path.insert(0, str(SAMPLE_DIR / "tools"))
    from register_skills import local_skills

    expected = {name for name, _path in local_skills()}
    listing = run_cli(["skill", "list"])
    found = set()
    for item in _entries(listing, "data", "entries", "skills"):
        if item.get("status") not in (None, "published"):
            continue
        if item.get("name"):
            found.add(str(item["name"]))
    return expected <= found


def build_checks(*, data_ok: bool, run_cli) -> list[dict]:
    capability_ok = capability_ready(run_cli)
    skill_ok = skills_ready(run_cli)
    checks = []
    for name in REQUIRED:
        if name in DATA_CHECKS:
            ok = data_ok
        elif name == "capability-callable":
            ok = capability_ok
        else:
            ok = skill_ok
        checks.append({"name": name, "ok": ok})
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
    if raw.get("sample") != "supply-chain":
        print("unexpected sample", file=sys.stderr)
        return 1
    config = os.environ.get("BKN_SAMPLE_CONFIG", "")
    if not config:
        print("missing BKN_SAMPLE_CONFIG", file=sys.stderr)
        return 1
    smoke = subprocess.run(
        [sys.executable, str(SAMPLE_DIR / "tools" / "smoke_test.py"), "--config", config],
        check=False,
    )
    checks = build_checks(data_ok=smoke.returncode == 0, run_cli=_openbkn)
    passed = all(item["ok"] for item in checks)
    body = {
        "ok": passed,
        "stage": "platform-verify",
        "resources": {
            "catalogId": raw["catalog"]["id"],
            "knowledgeNetworkId": raw["knowledgeNetwork"]["id"],
        },
        "checks": checks,
        "degrade": [],
        "message": "" if passed else "supply verification failed",
    }
    output = os.environ.get("BKN_SAMPLE_OUTPUT", "")
    if output:
        Path(output).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
