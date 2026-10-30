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
    product = _input("product", "string", "产品编码。", required=True)
    common = [
        _input("substitute_enabled", "boolean", "是否允许替代料；默认 false，用户允许时才传 true。"),
        _input("warehouse_scope", "string", "仓范围：all（默认，全公司）、finished_goods（三个成品仓）、production_available（苏州工厂生产七仓）。"),
        _input("need_by", "string", "需求日期 YYYY-MM-DD；传入后计入业务日期至该日（含）按交期到货的在途。不传只用现有库存。"),
        _input("chase_overdue_po", "boolean", "是否假设逾期在途都能催回来并计入；默认 false。"),
        _input("business_date", "string", "业务日期；默认 2026-08-25。"),
    ]
    if operation == "build_capacity":
        products = _input("products", "array", '产品编码列表，如 ["382-000005"]；多个产品各自独立计算，不共用库存。', required=True)
        products["sub_parameters"] = [{"name": "items", "type": "string", "required": True, "description": "产品编码。"}]
        return [products, *common]
    demands = _input("demands", "array", '需求列表，格式 [{"product":"382-000005","qty":50}]；数组顺序即扣减先后。', required=True)
    demands["sub_parameters"] = [{
        "name": "items", "type": "object", "required": True,
        "description": "一条需求。",
        "sub_parameters": [product, _input("qty", "number", "需求套数。", required=True)],
    }]
    return [demands, *common,
            _input("reserve_signed_backlog", "boolean", "是否先按承诺交期扣掉这些产品的已签约欠货；评估新单且要先保欠货时传 true，评估欠单本身时不传。"),
            _input("use_finished_goods", "boolean", "是否先用成品库存；默认 true，排生产工单时传 false。")]


def _call(args: list[str]) -> Any:
    completed = subprocess.run(
        ["openbkn", "--json", *args], check=False, capture_output=True, text=True
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"openbkn 调用失败（退出码 {completed.returncode}）")
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
                "description": "计算结果、业务依据和函数自行读取的数据量。",
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
                        "box_desc": "supply_ontology_hand 原生供应链计算函数；由 OpenBKN Function Runtime 执行。",
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
    parser.add_argument("--box-name", default="供应链原生计算函数")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--kn-id", help="Mount these functions to the target knowledge network")
    args = parser.parse_args()
    print(json.dumps(run(box_name=args.box_name, apply=args.apply, kn_id=args.kn_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
