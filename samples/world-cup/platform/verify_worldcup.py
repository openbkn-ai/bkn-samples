#!/usr/bin/env python3
"""Smoke-check the world-cup platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

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


def model_ready(run_cli) -> bool:
    for directory, command in (("object_types", "object-type"), ("relation_types", "relation-type"), ("concept_groups", "concept-group")):
        expected = {re.search(r"^id: (.+)$", path.read_text(), re.M).group(1)
                    for path in (SAMPLE_DIR / "kn" / directory).glob("*.bkn")}
        result = run_cli(["bkn", command, "list", KN_ID])
        entries = result if isinstance(result, list) else result.get("entries", [])
        if {entry.get("id") for entry in entries} != expected:
            return False
    return True


# The WC-2022 top scorer in the locked data: Kylian Mbappé, 8 non-own goals.
PROBE_INPUT = {"tournament_id": "WC-2022", "top": 1}
PROBE_TOP = {"player_id": "P-64077", "goals": 8}


def _entries(payload, *keys):
    for key in keys:
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def functions_ready(run_cli) -> bool:
    """Enabled and mounted is not enough: call one function and check its locked answer."""
    sys.path.insert(0, str(SAMPLE_DIR / "tools"))
    from register_functions import BOX_NAME, FUNCTIONS

    listing = run_cli(["toolbox", "list", "--keyword", BOX_NAME, "--limit", "100"])
    box = next((item for item in _entries(listing, "data", "entries") if item.get("box_name") == BOX_NAME), None)
    if not box:
        return False
    tools = {item.get("name"): item.get("tool_id") for item in _entries(run_cli(["tool", "list", "--toolbox", box["box_id"], "--all"]), "tools")
             if item.get("status") == "enabled"}
    expected = [spec["name"] for spec in FUNCTIONS.values()]
    if not all(tools.get(name) for name in expected):
        return False
    mounted = {item.get("capability_id") for item in _entries(run_cli(["bkn", "capability", "list", KN_ID, "--limit", "100"]), "entries")
               if item.get("capability_type") == "function"}
    if not {tools[name] for name in expected} <= mounted:
        return False
    try:
        executed = run_cli(["tool", "execute", tools[FUNCTIONS["top_scorers"]["name"]], "--toolbox", box["box_id"],
                            "--body", json.dumps(PROBE_INPUT)])
    except RuntimeError:
        return False
    rows = ((executed.get("body") or {}).get("result") or {}).get("rows") or []
    return bool(rows) and {k: rows[0].get(k) for k in PROBE_TOP} == PROBE_TOP


def build_checks(*, data_ok: bool, model_ok: bool, functions_ok: bool | None = None) -> list[dict]:
    checks = [{"name": name, "ok": data_ok} for name in DATA_CHECKS] + [{"name": "model-imported", "ok": model_ok}]
    if functions_ok is not None:
        checks.append({"name": "capability-callable", "ok": functions_ok})
    return checks


def _openbkn(args: list[str]) -> dict | list:
    completed = subprocess.run(["openbkn", "--json", *args], check=False, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError("openbkn command failed")
    payload = json.loads(completed.stdout or "{}")
    if not isinstance(payload, (dict, list)):
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
        model_ok = True
        functions_ok = True if raw.get("components", {}).get("functions") else None
    else:
        sys.path.insert(0, str(SAMPLE_DIR))
        from db.verify_worldcup import main as verify_database

        data_ok = verify_database() == 0
        model_ok = model_ready(_openbkn)
        functions_ok = functions_ready(_openbkn) if raw.get("components", {}).get("functions") else None
    checks = build_checks(data_ok=data_ok, model_ok=model_ok, functions_ok=functions_ok)
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
