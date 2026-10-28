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
LEGACY_TOOL_NAME = "supply_chain_compute"


def _input(name: str, type_: str, description: str, *, required: bool = False) -> dict[str, Any]:
    return {"name": name, "type": type_, "required": required, "description": description}


def _operation_inputs(operation: str) -> list[dict[str, Any]]:
    product = _input("product", "string", 'Product code.', required=True)
    substitute = _input("substitute_enabled", "boolean", 'Explicit alternate policy required for alternate analysis.')
    substitute_required = _input("substitute_enabled", "boolean", 'Explicitly set substitute_enabled to true or false.', required=True)
    scope = _input("warehouse_scope", "string", 'Warehouse preset or explicit warehouse list.')
    assurance = [product, _input("qty", "number", "Positive integer demand quantity.", required=True),
                 _input("demand_purpose", "string", "customer_delivery or new_production; required and never inferred.", required=True), _input("warehouse_scope", "string", "all (default), production_available or finished_goods.")]
    demands = _input("demands", "array", 'At least two demands, such as [{"product":"382-000005","qty":50},{"product":"P61-000351","qty":60}]. Array order sets allocation priority.', required=True)
    demands["sub_parameters"] = [{
        "name": "items", "type": "object", "required": True,
        "description": 'One demand, in allocation priority order.',
        "sub_parameters": [product, _input("qty", "number", 'Required number of product sets.', required=True)],
    }]
    cases = {
        "shortage_rule": [_input("event_source", "object", "Resolved event object/relation IDs, demand/shortage event types and verified/processing/closed lifecycle codes (sample adapter v1).", required=True),
                          _input("window_start", "string", "Inclusive RFC3339 boundary with explicit timezone; fixed across retries.", required=True),
                          _input("window_end", "string", "Exclusive RFC3339 boundary with explicit timezone; fixed across retries.", required=True)],
        "material_coverage": assurance,
        "replenishment_draft": [_input("coverage", "object", "Complete material_coverage result; structure is checked but facts are not requeried. Draft only, no persistence or business writes.", required=True)],
        "bom_list": [product, _input("depth", "number", 'Expansion depth; default one level.'), _input("include_substitute", "boolean", 'Include alternate BOM rows.'), _input("report_grain", "string", 'Report grain; summary gives structure counts and first-level main components; full returns paged details.'), _input("page_size", "number", 'Full-detail page size, from 1 to 500.'), _input("offset", "number", 'Start offset for full details; default 0.')],
        "bom_shared_list": [_input("products", "array", 'At least two product codes.', required=True), _input("depth", "number", 'Expansion depth; default all levels.'), _input("include_substitute", "boolean", 'Include alternate BOM rows.')],
        "material_where_used": [_input("material_code", "string", 'Material code.', required=True), _input("include_substitute", "boolean", 'Include alternate branches in affected products; default true.'), _input("report_grain", "string", 'Report grain; summary by default, full for matching BOM paths.')],
        "layered_inventory": [product, _input("depth", "number", 'Expansion depth; default one level.'), scope, _input("include_substitute", "boolean", 'Include alternate BOM rows.')],
        "substitute_status": [_input("product", "string", 'Product code; provide this or material_code, not both.'), _input("material_code", "string", 'Material code; provide this or product, not both.'), scope, substitute],
        "theoretical_build": [product, scope, substitute, _input("report_grain", "string", 'Report grain; summary by default, full for all material constraints.')],
        "total_sellable": [product, _input("production_scope", "string", 'Production warehouse scope.'), _input("finished_goods_scope", "string", 'Finished goods warehouse scope.'), substitute],
        "kitting_net_demand": [product, _input("qty", "number", 'Required sets.', required=True), scope, substitute, _input("report_grain", "string", 'summary includes complete gaps and their net/replenishment quantities; full additionally includes all allocation lines. Do not request full merely to obtain shortage quantities.')],
        "shared_contention": [demands, scope, substitute_required, _input("report_grain", "string", 'Report grain; summary by default, full for per-material allocation and the entire remaining pool.')],
        "max_build_without_po": [product, scope, substitute, _input("report_grain", "string", 'Report grain; summary by default, full for all material constraints.')],
        "leadtime_days": [_input("material_code", "string", 'Material code.', required=True)],
        "supply_status": [_input("material_code", "string", 'Material code.', required=True), _input("due_date", "string", 'Required arrival or delivery date.'), _input("gross_requirement", "number", 'Gross required quantity.'), scope, _input("child_short", "boolean", 'Whether a child material is already short.')],
        "open_forecast_count": [_input("product_code", "string", 'Optional product code; omit to count all open forecasts.'), _input("report_grain", "string", 'Report grain; summary by default, full for forecast ID lists.')],
        "backward_plan": [_input("product", "string", 'New demand product code; optional for an existing forecast.'), _input("forecast_id", "string", 'Existing forecast ID, preserving leading zeroes, such as 0000023181. The function reads product, quantity and deadline automatically.'), _input("demand_end", "string", 'New demand deadline in YYYY-MM-DD; optional for an existing forecast.'), _input("demand_qty", "number", 'New demand quantity; optional for an existing forecast.'), _input("business_date", "string", 'Business date; default 2026-08-25.'), scope, substitute_required, _input("report_grain", "string", 'Report grain; default summary.')],
    }
    return cases[operation]


def _call(args: list[str]) -> Any:
    completed = subprocess.run(
        ["openbkn", "--json", *args], check=False, capture_output=True, text=True
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"""openbkn call failed (exit code {completed.returncode})""")
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
                "description": ('Draft from supplied coverage: structure checked, not requeried or persisted.' if operation == 'replenishment_draft' else 'Result, business evidence and runtime data sources read by the function.'),
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
                        "box_desc": 'Supply EN functions executed by OpenBKN Function Runtime.',
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
    legacy = _find_tool(box_id, LEGACY_TOOL_NAME)
    if legacy and legacy.get("status") != "disabled":
        _call(["tool", "disable", "--toolbox", box_id, legacy["tool_id"]])
    if kn_id:
        from bind_draft_action import bind_draft_action
        bind_draft_action(_call, kn_id, box_id, tool_ids["replenishment_draft"])
        _call(["bkn", "capability", "attach", kn_id, "--box", box_id,
               "--tool", ",".join(tool_ids.values())])
    return {**preview, "box_id": box_id, "tool_ids": tool_ids, "legacy_tool_disabled": bool(legacy)}


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
