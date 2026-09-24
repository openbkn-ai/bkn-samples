#!/usr/bin/env python3
"""Smoke-check the supply-chain platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REQUIRED = ("tables-discovered", "object-query", "cross-table-query", "capability-callable", "skill-discoverable")
SAMPLE_DIR = Path(__file__).resolve().parents[1]


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
    passed = smoke.returncode == 0
    checks = [{"name": name, "ok": passed} for name in REQUIRED]
    body = {
        "ok": passed,
        "stage": "platform-verify",
        "resources": {
            "catalogId": raw["catalog"]["id"],
            "knowledgeNetworkId": raw["knowledgeNetwork"]["id"],
        },
        "checks": checks,
        "degrade": [],
        "message": "",
    }
    output = os.environ.get("BKN_SAMPLE_OUTPUT", "")
    if output:
        Path(output).write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
