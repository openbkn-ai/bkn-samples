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

try:
    from installer.sample_logging import run as run_sample_command
except ImportError:
    # Older installers retain the original subprocess behavior.
    run_sample_command = subprocess.run
from typing import Any

from ownership_receipt import require_owned, remember
from function_catalog import FUNCTION_CATALOG, KIT_PLAN_ACTIONS, KIT_SCHEDULE, SCHEDULE_RULES
from native_function_bundle import build_native_function_code


API = "/api/agent-operator-integration/v1"
BKN_API = "/api/bkn-backend/v1"
# Inputs the sample fixes instead of asking for: every run uses the sample's business date.
FIXED_INPUTS = {"business_date"}


def _input(name: str, type_: str, description: str, *, required: bool = False) -> dict[str, Any]:
    return {"name": name, "type": type_, "required": required, "description": description}


def _operation_inputs(operation: str) -> list[dict[str, Any]]:
    product = _input("product", "string", "Product code.", required=True)
    common = [
        _input("substitute_enabled", "boolean", "Allow alternates; default false, pass true only when the user allows them."),
        _input("warehouse_scope", "string", "Warehouse scope: all (default, every warehouse), finished_goods (the three finished-goods warehouses), production_available (the seven Suzhou plant production warehouses)."),
        _input("need_by", "string", "Need-by date YYYY-MM-DD; adds open purchase lines due from the business date through that date. Omit to use current stock only."),
        _input("chase_overdue_po", "boolean", "Assume every overdue open purchase line is chased back and count it; default false."),
        _input("business_date", "string", "Business date; default 2027-02-25."),
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


KIT_INPUTS = [
    ("bill_no", "Forecast number."),
    ("product_code", "Product code; an empty string schedules the whole bill."),
    ("line_code", "Line code; the products must belong to the line's product lines."),
    ("planned_start", "Planned start, a date or date-time; a date alone starts at 08:00."),
    ("planned_finish", "Planned finish, a date or date-time; a date alone finishes at 20:00."),
    ("plan_status", "Plan status: Scheduled, Confirmed or Cancelled; new plans are usually Scheduled, Cancelled cancels the plan."),
    ("source_scenario", "Name of the adopted scenario, for traceability."),
    ("planner", "Planner."),
    ("plan_id", "Plan to adjust or cancel; omit when creating."),
]
# Parameters of the three plan actions: property = the new object's input (create) or the selected
# plan's value (adjust, cancel); input = what the caller decides; const = fixed by the action.
KIT_ACTION_PARAMETERS = {
    "create": {"bill_no": "property", "product_code": "property", "line_code": "property", "planned_start": "property",
               "planned_finish": "property", "plan_status": "property", "source_scenario": "property", "planner": "property"},
    "adjust": {"plan_id": "property", "bill_no": "property", "product_code": "property", "plan_status": "property",
               "line_code": "input", "planned_start": "input", "planned_finish": "input", "source_scenario": "input",
               "planner": "input"},
    "cancel": {"plan_id": "property", "bill_no": "property", "product_code": "property", "plan_status": ("const", "Cancelled"),
               "planner": "input"},
}


def rule_tool_inputs() -> list[dict[str, Any]]:
    """The schedule-Gantt rule-tool contract: tasks in, one result per task out."""
    task = {"name": "items", "type": "object", "required": True, "description": "One task: key, start, end, resource, values."}
    tasks = _input("tasks", "array", "Tasks to check, at most 200 per call; values carry bill_no, product_code, line_code, planned_start, plan_status.")
    tasks["sub_parameters"] = [task]
    return [tasks, _input("scenario", "object", "Scenario edits; the tasks already carry the edited values, so it may be omitted."),
            _input("mode", "string", "detail for one task's detail table (Kit_Check only); omit for the batch check."),
            _input("task", "object", "The task of a detail call, shaped like one item of tasks."),
            _input("locale", "string", "Label language of the detail: zh-CN or en-US."),
            _input("query", "object", "Detail filter and paging: group, keyOnly, search, offset, limit (default 50).")]


def rule_action_definitions(kn_id: str, box_id: str, tool_ids: dict[str, str]) -> list[dict[str, Any]]:
    """The rule tools as tool actions, so Q&A and Skills check plans with the same code as the Gantt."""
    return [{
        "id": f"{kn_id}_{operation}", "name": spec["name"], "branch": "main",
        "operation_config": {"type": "tool"}, "object_type_id": "", "action_type": "modify", "action_intent": "modify",
        "action_source": {"type": "tool", "box_id": box_id, "tool_id": tool_ids[operation]},
        "parameters": [{"name": "tasks", "type": "array", "value_from": "input", "comment": rule_tool_inputs()[0]["description"]}],
        "comment": f"{spec['description']}\n{spec['use_rule']}",
    } for operation, spec in SCHEDULE_RULES.items()]


def kit_tool_inputs() -> list[dict[str, Any]]:
    return [_input(name, "string", description) for name, description in KIT_INPUTS]


def kit_action_definitions(kn_id: str, box_id: str, tool_id: str) -> list[dict[str, Any]]:
    """Three object actions on the plan object, all run by the kit-schedule Function."""
    descriptions = dict(KIT_INPUTS)
    actions = []
    for key, (name, action_type, comment) in KIT_PLAN_ACTIONS.items():
        parameters = []
        for param, source in KIT_ACTION_PARAMETERS[key].items():
            kind, value = source if isinstance(source, tuple) else (source, param)
            item = {"name": param, "type": "string", "value_from": kind, "comment": descriptions[param]}
            if kind != "input":
                item["value"] = value
            parameters.append(item)
        actions.append({
            "id": f"{kn_id}_kitplan_{key}", "name": name, "branch": "main",
            "operation_config": {"type": "object"}, "object_type_id": f"{kn_id}_kitplan",
            "action_type": action_type, "action_intent": action_type,
            "action_source": {"type": "tool", "box_id": box_id, "tool_id": tool_id},
            "parameters": parameters, "comment": f"{comment}\n{KIT_SCHEDULE['use_rule']}",
        })
    return actions


def action_definitions(kn_id: str, box_id: str, tool_ids: dict[str, str]) -> list[dict[str, Any]]:
    """One tool action per function: a business judgement whose assumptions are explicit inputs.

    The platform requires every input parameter, so the Agent states each assumption (or its
    documented default) on every run and the execution record shows what the answer assumed.
    """
    actions = []
    for operation, spec in FUNCTION_CATALOG.items():
        parameters = [
            {"name": item["name"], "type": item["type"], "value_from": "input", "comment": item["description"]}
            for item in _operation_inputs(operation)
            if item["name"] not in FIXED_INPUTS
        ]
        actions.append({
            "id": f"{kn_id}_{operation}",
            "name": spec["name"],
            "branch": "main",
            "operation_config": {"type": "tool"},
            "object_type_id": "",
            "action_type": "modify",
            "action_intent": "modify",
            "action_source": {"type": "tool", "box_id": box_id, "tool_id": tool_ids[operation]},
            "parameters": parameters,
            "comment": f"{spec['description']}\n{spec['use_rule']}",
        })
    return actions


def _call(args: list[str]) -> Any:
    completed = run_sample_command(
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
    tools = {
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
    tools["kit_schedule"] = {
        "name": KIT_SCHEDULE["name"], "description": KIT_SCHEDULE["description"], "script_type": "python",
        "code": build_native_function_code(fixed_operation="kit_schedule"), "inputs": kit_tool_inputs(),
        "outputs": [{"name": "result", "type": "object", "required": True,
                     "description": "The plan written (plan ID, kit status, kit date, key material, shortage note) and the shortages."}],
    }
    for operation, spec in SCHEDULE_RULES.items():
        tools[operation] = {
            "name": spec["name"], "description": spec["description"], "script_type": "python",
            "code": build_native_function_code(fixed_operation=operation), "inputs": rule_tool_inputs(),
            "outputs": [{"name": "results", "type": "array", "required": False,
                         "description": "Check: one result per task (key, pass, severity, text, related, at, counts, detail); a detail call returns the table."}],
        }
    return tools


def _use_rule(operation: str) -> str:
    if operation in SCHEDULE_RULES:
        return SCHEDULE_RULES[operation]["use_rule"]
    return KIT_SCHEDULE["use_rule"] if operation == "kit_schedule" else FUNCTION_CATALOG[operation]["use_rule"]


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
                        "box_desc": "Supply EN calculation and kit-schedule functions executed by OpenBKN Function Runtime.",
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
                json.dumps({"metadata_type": "function", "use_rule": _use_rule(operation), "function_input": tool_input}, ensure_ascii=False),
            ])
            tool_id = created["success_ids"][0]
            _call(["tool", "enable", "--toolbox", box_id, tool_id])
        else:
            tool_id = tool["tool_id"]
            _call([
                "call", f"{API}/tool-box/{box_id}/tool/{tool_id}", "-X", "POST", "-d",
                json.dumps({"name": tool_input["name"], "description": tool_input["description"], "use_rule": _use_rule(operation), "metadata_type": "function", "function_input": tool_input}, ensure_ascii=False),
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
    actions: list[dict[str, Any]] = []
    if kn_id:
        actions = [*action_definitions(kn_id, box_id, {k: v for k, v in tool_ids.items() if k in FUNCTION_CATALOG}),
                   *kit_action_definitions(kn_id, box_id, tool_ids["kit_schedule"]),
                   *rule_action_definitions(kn_id, box_id, tool_ids)]
        # Overwrite keeps a repeated install idempotent and follows re-created tool IDs.
        _call(["call", f"{BKN_API}/knowledge-networks/{kn_id}/action-types?import_mode=overwrite",
               "-X", "POST", "-d", json.dumps({"entries": actions}, ensure_ascii=False)])
    return {**preview, "box_id": box_id, "tool_ids": tool_ids,
            "action_ids": [item["id"] for item in actions] if kn_id else [],
            "retired_tools": [item["name"] for item in retired]}


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
