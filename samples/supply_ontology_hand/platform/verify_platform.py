#!/usr/bin/env python3
"""Smoke-check the supply-chain platform hook. Does not call kubectl."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

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
    sys.path.insert(0, str(SAMPLE_DIR / "tools"))
    from function_catalog import FUNCTION_CATALOG

    expected = {spec["name"] for spec in FUNCTION_CATALOG.values()}
    if not expected:
        return False
    listing = run_cli(["toolbox", "list", "--keyword", BOX_NAME, "--limit", "100"])
    box = next((item for item in _entries(listing, "data", "entries") if item.get("box_name") == BOX_NAME), None)
    if not box or not box.get("box_id"):
        return False
    tools = run_cli(["tool", "list", "--toolbox", box["box_id"], "--all"])
    enabled = {item.get("name"): item.get("tool_id")
               for item in _entries(tools, "tools", "data", "entries")
               if item.get("status") == "enabled" and item.get("tool_id")}
    if not expected <= enabled.keys():
        return False
    bindings = run_cli(["bkn", "capability", "list", "supply_ontology_hand", "--limit", "100"])
    mounted = {item.get("capability_id") for item in _entries(bindings, "entries")
               if item.get("capability_type") == "function" and item.get("box_id") == box["box_id"]}
    if not {enabled[name] for name in expected} <= mounted:
        return False
    return function_reads_network(run_cli, box["box_id"], enabled[FUNCTION_CATALOG["leadtime_days"]["name"]])


# Material 606-000989 is a purchased part with a 14-day purchase lead time in the locked data.
PROBE_INPUT = {"material_code": "606-000989"}
PROBE_LEADTIME_DAYS = 14


def function_reads_network(run_cli, box_id: str, tool_id: str) -> bool:
    """Enabled and mounted does not prove a function can read the network; call one."""
    try:
        executed = run_cli(["tool", "execute", tool_id, "--toolbox", box_id, "--body", json.dumps(PROBE_INPUT)])
    except RuntimeError:
        return False
    result = (executed.get("body") or {}).get("result") or {}
    return result.get("leadtime_days") == PROBE_LEADTIME_DAYS


def skills_ready(run_cli) -> bool:
    sys.path.insert(0, str(SAMPLE_DIR / "tools"))
    from register_skills import local_skills

    expected = {name for name, _path in local_skills()}
    listing = run_cli(["skill", "list", "--all"])
    found = {}
    for item in _entries(listing, "data", "entries", "skills"):
        if item.get("status") not in (None, "published"):
            continue
        if item.get("name"):
            found[str(item["name"])] = item.get("skill_id") or item.get("id")
    if not expected <= found.keys() or not all(found[name] for name in expected):
        return False
    bindings = run_cli(["bkn", "capability", "list", "supply_ontology_hand", "--limit", "100"])
    mounted = {item.get("capability_id") for item in _entries(bindings, "entries")
               if item.get("capability_type") == "skill"}
    return {found[name] for name in expected} <= mounted


def build_checks(*, data_ok: bool, run_cli, components: dict) -> list[dict]:
    checks = [{"name": name, "ok": data_ok} for name in DATA_CHECKS]
    if components.get("functions"):
        checks.append({"name": "capability-callable", "ok": capability_ready(run_cli)})
    if components.get("skills"):
        checks.append({"name": "skill-discoverable", "ok": skills_ready(run_cli)})
    return checks


def metric_checks(report: dict, command_ok: bool) -> list[dict]:
    checks = []
    for section, name in (("verify_metrics", "metric-query"),
                          ("verify_metric_ownership", "metric-ownership")):
        result = report.get(section) or {}
        checks.append({"name": name, "ok": bool(command_ok and result.get("passed")
                                               and result.get("failed") == [])})
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
    document = yaml.safe_load((SAMPLE_DIR / "sample.yaml").read_text(encoding="utf-8"))
    checks = build_checks(
        data_ok=smoke.returncode == 0,
        run_cli=_openbkn,
        components=document["spec"]["components"],
    )
    if document["spec"]["components"].get("metrics"):
        metrics = subprocess.run(
            [sys.executable, str(SAMPLE_DIR / "tools" / "power_layer.py"), "verify",
             "--kn-id", raw["knowledgeNetwork"]["id"]],
            check=False, capture_output=True, text=True,
        )
        try:
            report = json.loads(metrics.stdout)
            if not isinstance(report, dict):
                report = {}
        except ValueError:
            report = {}
        checks.extend(metric_checks(report, metrics.returncode == 0))
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
