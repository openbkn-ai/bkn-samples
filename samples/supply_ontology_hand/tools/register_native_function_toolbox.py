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

from function_catalog import FUNCTION_CATALOG
from native_function_bundle import build_native_function_code


API = "/api/agent-operator-integration/v1"
LEGACY_TOOL_NAME = "supply_chain_compute"


def _input(name: str, type_: str, description: str, *, required: bool = False) -> dict[str, Any]:
    return {"name": name, "type": type_, "required": required, "description": description}


def _operation_inputs(operation: str) -> list[dict[str, Any]]:
    product = _input("product", "string", "产品编码。", required=True)
    substitute = _input("substitute_enabled", "boolean", "是否启用替代料；需要替代判断时必须明确。")
    substitute_required = _input("substitute_enabled", "boolean", "是否启用替代料；必须明确传 true 或 false。", required=True)
    scope = _input("warehouse_scope", "string", "仓范围预设或明确仓库列表。")
    cases = {
        "bom_list": [product, _input("depth", "number", "展开层数；不传为一层。"), _input("include_substitute", "boolean", "是否包含替代料行。"), _input("report_grain", "string", "结果粒度；默认 summary 返回结构统计和一级主料，传 full 才返回明细。"), _input("page_size", "number", "full 明细的单页行数，1 到 500。"), _input("offset", "number", "full 明细的起始偏移量，默认 0。")],
        "bom_shared_list": [_input("products", "array", "至少两个产品编码。", required=True), _input("depth", "number", "展开层数；不传为全层。"), _input("include_substitute", "boolean", "是否包含替代料行。")],
        "material_where_used": [_input("material_code", "string", "物料编码。", required=True), _input("include_substitute", "boolean", "是否将替代料分支计入受影响产品；默认 true。"), _input("report_grain", "string", "结果粒度；默认 summary，传 full 返回命中 BOM 路径。")],
        "layered_inventory": [product, _input("depth", "number", "展开层数；不传为一层。"), scope, _input("include_substitute", "boolean", "是否包含替代料行。")],
        "substitute_status": [_input("product", "string", "产品编码；与物料编码二选一。"), _input("material_code", "string", "物料编码；与产品编码二选一。"), scope, substitute],
        "theoretical_build": [product, scope, substitute, _input("report_grain", "string", "结果粒度；默认 summary，传 full 返回全部物料约束。")],
        "total_sellable": [product, _input("production_scope", "string", "生产仓范围。"), _input("finished_goods_scope", "string", "成品仓范围。"), substitute],
        "kitting_net_demand": [product, _input("qty", "number", "需求套数。", required=True), scope, substitute, _input("report_grain", "string", "结果粒度；默认 summary，传 full 返回全部物料明细。")],
        "shared_contention": [_input("demands", "array", '至少两条对象需求，格式 [{"product":"382-000005","qty":50},{"product":"P61-000351","qty":60}]；数组顺序即扣减优先级。', required=True), scope, substitute_required, _input("report_grain", "string", "结果粒度；默认 summary，传 full 返回逐料分配和完整剩余池。")],
        "max_build_without_po": [product, scope, substitute, _input("report_grain", "string", "结果粒度；默认 summary，传 full 返回全部物料约束。")],
        "leadtime_days": [_input("material_code", "string", "物料编码。", required=True)],
        "supply_status": [_input("material_code", "string", "物料编码。", required=True), _input("due_date", "string", "到位日或交货日。"), _input("gross_requirement", "number", "毛需求数量。"), scope, _input("child_short", "boolean", "是否已有子件短缺。")],
        "open_forecast_count": [_input("product_code", "string", "可选产品编码；不传统计全部未关闭预测单。"), _input("report_grain", "string", "结果粒度；默认 summary，传 full 返回预测单 ID 列表。")],
        "backward_plan": [_input("product", "string", "新增需求的产品编码；预测单模式可不传。"), _input("forecast_id", "string", "已有预测单 id；允许前导零，例如 0000023181。传入后函数自动读取产品、数量和截止日。"), _input("demand_end", "string", "新增需求的交付截止日 YYYY-MM-DD；预测单模式可不传。"), _input("demand_qty", "number", "新增需求数量；预测单模式可不传。"), _input("business_date", "string", "业务基准日；不传使用样例默认 2026-08-25。"), scope, substitute_required, _input("report_grain", "string", "报告粒度，默认 summary。")],
    }
    return cases[operation]


def _call(args: list[str]) -> Any:
    completed = subprocess.run(
        ["openbkn", "--json", *args], check=False, capture_output=True, text=True
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"openbkn 调用失败（退出码 {completed.returncode}）")
    return json.loads(completed.stdout)


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
                "description": "计算结果、业务依据和函数自行读取的数据来源。",
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


def run(*, box_name: str, apply: bool) -> dict[str, Any]:
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
    box_id = box["box_id"]
    tool_ids: dict[str, str] = {}
    for operation, tool_input in tool_inputs.items():
        tool = _find_tool(box_id, tool_input["name"])
        if tool is None:
            created = _call([
                "call", f"{API}/tool-box/{box_id}/tool", "-X", "POST", "-d",
                json.dumps({"metadata_type": "function", "function_input": tool_input}, ensure_ascii=False),
            ])
            tool_id = created["success_ids"][0]
            _call(["tool", "enable", "--toolbox", box_id, tool_id])
        else:
            tool_id = tool["tool_id"]
            _call([
                "call", f"{API}/tool-box/{box_id}/tool/{tool_id}", "-X", "POST", "-d",
                json.dumps({"name": tool_input["name"], "description": tool_input["description"], "metadata_type": "function", "function_input": tool_input}, ensure_ascii=False),
            ])
            if tool.get("status") != "enabled":
                _call(["tool", "enable", "--toolbox", box_id, tool_id])
        tool_ids[operation] = tool_id
    if box.get("status") != "published":
        _call(["toolbox", "publish", box_id])
    legacy = _find_tool(box_id, LEGACY_TOOL_NAME)
    if legacy and legacy.get("status") != "disabled":
        _call(["tool", "disable", "--toolbox", box_id, legacy["tool_id"]])
    return {**preview, "box_id": box_id, "tool_ids": tool_ids, "legacy_tool_disabled": bool(legacy)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--box-name", default="供应链原生计算函数")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(box_name=args.box_name, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
