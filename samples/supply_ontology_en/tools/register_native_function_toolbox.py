#!/usr/bin/env python3
"""Register one discoverable native Function Tool per supply operation.

This is the default third-party path: it needs only an authenticated OpenBKN
CLI profile.  No function server, container, host name, or service URL exists
in this flow.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any

from ownership_receipt import require_owned, remember
from function_catalog import FUNCTION_CATALOG
from native_function_bundle import build_native_function_code


API = "/api/agent-operator-integration/v1"


def _input(name: str, type_: str, description: str, *, required: bool = False) -> dict[str, Any]:
    return {"name": name, "type": type_, "required": required, "description": description}


def _operation_inputs(operation: str) -> list[dict[str, Any]]:
    product = _input("product", "string", "Product code.", required=True)
    common = [
        _input("substitute_enabled", "boolean", "Allow alternates; default false, pass true only when the user allows them."),
        _input("warehouse_scope", "string", "Warehouse scope: all (default, every warehouse), finished_goods (the three finished-goods warehouses), production_available (the seven Suzhou plant production warehouses)."),
        _input("need_by", "string", "Need-by date YYYY-MM-DD; adds open purchase lines due from the business date through that date. Omit to use current stock only."),
        _input("chase_overdue_po", "boolean", "Assume every overdue open purchase line is chased back and count it; default false."),
        _input("business_date", "string", "Business date; default 2026-08-25."),
    ]
    if operation == "build_capacity":
        products = _input("products", "array", 'Product codes, e.g. ["382-000005"]; each product is calculated on its own, without sharing stock.', required=True)
        products["sub_parameters"] = [{"name": "items", "type": "string", "required": True, "description": "Product code."}]
        return [products, *common]
    demands = _input("demands", "array", 'Demands as [{"product":"382-000005","qty":50}]; array order is allocation order.', required=True)
    demands["sub_parameters"] = [{
        "name": "items", "type": "object", "required": True,
        "description": "One demand.",
        "sub_parameters": [product, _input("qty", "number", "Units required.", required=True)],
    }]
    return [demands, *common,
            _input("reserve_signed_backlog", "boolean", "Reserve these products' signed backlog by promised date first; pass true for new orders that must protect backlog, omit when evaluating the backlog itself."),
            _input("use_finished_goods", "boolean", "Use finished goods first; default true, pass false when planning a work order.")]


def _call(args: list[str]) -> Any:
    completed = subprocess.run(
        ["openbkn", "--json", *args], check=False, capture_output=True, text=True
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"openbkn call failed (exit code {completed.returncode})")
    output = completed.stdout.strip()
    if not output and args[0] == "call" and "-X" in args and args[args.index("-X") + 1] == "PUT":
        return {}
    return json.loads(output)


def _tool_inputs() -> dict[str, dict[str, Any]]:
    return {
        operation: {
        "name": spec["name"],
        "description": spec["description"],
        "script_type": "python",
        "code": build_native_function_code(fixed_operation=operation),
        "inputs": _operation_inputs(operation),
        "outputs": [
            {
                "name": "result",
                "type": "object",
                "required": True,
                "description": "Result, business basis and the row counts the function read.",
            }
        ],
        }
        for operation, spec in FUNCTION_CATALOG.items()
    }


def _find_exact_box(name: str) -> dict[str, Any] | None:
    listing = _call(["toolbox", "list", "--keyword", name, "--limit", "100"])
    for item in listing.get("data", listing.get("entries", [])):
        if item.get("box_name") == name:
            return item
    return None


def _find_tool(box_id: str, name: str) -> dict[str, Any] | None:
    listing = _call(["tool", "list", "--toolbox", box_id, "--all"])
    for item in listing.get("tools", []):
        if item.get("name") == name:
            return item
    return None


def run(*, box_name: str, apply: bool, kn_id: str | None = None) -> dict[str, Any]:
    tool_inputs = _tool_inputs()
    preview = {
        "mode": "apply" if apply else "dry_run",
        "box_name": box_name,
        "metadata_type": "function",
        "tool_names": [item["name"] for item in tool_inputs.values()],
        "operations": list(tool_inputs),
        "entrypoint": "@tool business-parameter entrypoint",
        "needs_external_service": False,
        "code_bytes_per_tool": len(next(iter(tool_inputs.values()))["code"].encode("utf-8")),
    }
    if not apply:
        return preview

    box = _find_exact_box(box_name)
    if box is not None:
        require_owned("toolboxes", box["box_id"])
    if box is None:
        box = _call(
            [
                "call",
                f"{API}/tool-box",
                "-X",
                "POST",
                "-d",
                json.dumps(
                    {
                        "box_name": box_name,
                        "box_desc": "Supply EN functions executed by OpenBKN Function Runtime.",
                        "box_category": "data_process",
                        "metadata_type": "function",
                        "source": "custom",
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        remember("toolboxes", box["box_id"])
    box_id = box["box_id"]
    tool_ids: dict[str, str] = {}
    for operation, tool_input in tool_inputs.items():
        tool = _find_tool(box_id, tool_input["name"])
        if tool is None:
            created = _call([
                "call", f"{API}/tool-box/{box_id}/tool", "-X", "POST", "-d",
                json.dumps({"metadata_type": "function", "use_rule": FUNCTION_CATALOG[operation]["use_rule"], "function_input": tool_input}, ensure_ascii=False),
            ])
            tool_id = created["success_ids"][0]
            _call(["tool", "enable", "--toolbox", box_id, tool_id])
        else:
            tool_id = tool["tool_id"]
            _call([
                "call", f"{API}/tool-box/{box_id}/tool/{tool_id}", "-X", "POST", "-d",
                json.dumps({"name": tool_input["name"], "description": tool_input["description"], "use_rule": FUNCTION_CATALOG[operation]["use_rule"], "metadata_type": "function", "function_input": tool_input}, ensure_ascii=False),
            ])
            if tool.get("status") != "enabled":
                _call(["tool", "enable", "--toolbox", box_id, tool_id])
        tool_ids[operation] = tool_id
    if box.get("status") != "published":
        _call(["toolbox", "publish", box_id])
    current = {item["name"] for item in tool_inputs.values()}
    retired = [item for item in _call(["tool", "list", "--toolbox", box_id, "--all"]).get("tools", [])
               if item.get("name") not in current and item.get("status") != "disabled"]
    for item in retired:
        _call(["tool", "disable", "--toolbox", box_id, item["tool_id"]])
    if kn_id:
        _call(["bkn", "capability", "attach", kn_id, "--box", box_id,
               "--tool", ",".join(tool_ids.values())])
    return {**preview, "box_id": box_id, "tool_ids": tool_ids, "retired_tools": [item["name"] for item in retired]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--box-name", default='Supply_EN_Functions')
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--kn-id", help="Mount these functions to the target knowledge network")
    args = parser.parse_args()
    print(json.dumps(run(box_name=args.box_name, apply=args.apply, kn_id=args.kn_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
