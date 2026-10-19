#!/usr/bin/env python3
"""Publish the World Cup native functions and mount them to the knowledge network.

Each function in functions/ is one self-contained file published verbatim as the
Function code. It reads the network through the sandbox's preinstalled bkn_osdk;
the gateway and credentials come from the runtime, never from this code.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS.parent / "platform"))
from ownership_receipt import remember, require_owned  # noqa: E402

API = "/api/agent-operator-integration/v1"
BOX_NAME = "世界杯函数"


def _input(name: str, type_: str, description: str, *, required: bool = False) -> dict[str, Any]:
    return {"name": name, "type": type_, "required": required, "description": description}


FUNCTIONS = {
    "top_scorers": {
        "name": "射手榜",
        "description": "按非乌龙球进球数给球员做竞赛排名（并列同名次，保留边界处全部并列者）。"
                       "可按单届赛事 tournament_id（如 WC-2022）或 competition=men/women 筛选，top 为名次上限，默认 10。",
        "inputs": [
            _input("tournament_id", "string", "单届赛事 ID，如 WC-2022；与 competition 二选一。"),
            _input("competition", "string", "men 或 women；与 tournament_id 二选一。"),
            _input("top", "number", "名次上限，1 到 100，默认 10。"),
        ],
    },
    "player_career": {
        "name": "球员生涯",
        "description": "一名球员的参赛届数（按大名单不同赛事计数）、非乌龙球进球合计与逐届明细、所获奖项。"
                       "传 player_id，或传 family_name（可加 given_name）；同名多人时返回候选列表。",
        "inputs": [
            _input("player_id", "string", "球员 ID，如 P-14758。"),
            _input("given_name", "string", "名（源数据为英文拼写）。"),
            _input("family_name", "string", "姓（源数据为英文拼写），不传 player_id 时必填。"),
        ],
    },
    "tournament_summary": {
        "name": "赛事概况",
        "description": "一届赛事的比赛数、比分进球（不含点球大战）、场均进球（三位小数）、进球事件数、乌龙球数和点球大战罚球数。",
        "inputs": [_input("tournament_id", "string", "赛事 ID，如 WC-2022。", required=True)],
    },
}


def function_code(operation: str) -> str:
    return (TOOLS / "functions" / f"{operation}.py").read_text(encoding="utf-8")


def _call(args: list[str]) -> Any:
    completed = subprocess.run(["openbkn", "--json", *args], check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"openbkn call failed (exit code {completed.returncode})")
    return json.loads(completed.stdout)


def _tool_input(operation: str) -> dict[str, Any]:
    spec = FUNCTIONS[operation]
    return {
        "name": spec["name"],
        "description": spec["description"],
        "script_type": "python",
        "code": function_code(operation),
        "inputs": spec["inputs"],
        "outputs": [{"name": "result", "type": "object", "required": True, "description": "计算结果及口径说明。"}],
    }


def _find_box(name: str) -> dict[str, Any] | None:
    listing = _call(["toolbox", "list", "--keyword", name, "--limit", "100"])
    return next((item for item in listing.get("data", listing.get("entries", [])) if item.get("box_name") == name), None)


def _find_tool(box_id: str, name: str) -> dict[str, Any] | None:
    listing = _call(["tool", "list", "--toolbox", box_id, "--all"])
    return next((item for item in listing.get("tools", []) if item.get("name") == name), None)


def run(*, apply: bool, kn_id: str | None) -> dict[str, Any]:
    preview = {"mode": "apply" if apply else "dry_run", "box_name": BOX_NAME,
               "functions": {op: spec["name"] for op, spec in FUNCTIONS.items()}}
    if not apply:
        return preview
    box = _find_box(BOX_NAME)
    if box is not None:
        require_owned("toolboxes", box["box_id"])
    else:
        box = _call(["call", f"{API}/tool-box", "-X", "POST", "-d", json.dumps({
            "box_name": BOX_NAME, "box_desc": "世界杯样例原生函数；由 OpenBKN Function Runtime 执行。",
            "box_category": "data_process", "metadata_type": "function", "source": "custom"}, ensure_ascii=False)])
        remember("toolboxes", box["box_id"])
    box_id = box["box_id"]
    tool_ids = {}
    for operation in FUNCTIONS:
        payload = _tool_input(operation)
        tool = _find_tool(box_id, payload["name"])
        if tool is None:
            created = _call(["call", f"{API}/tool-box/{box_id}/tool", "-X", "POST", "-d",
                             json.dumps({"metadata_type": "function", "function_input": payload}, ensure_ascii=False)])
            tool_id = created["success_ids"][0]
        else:
            tool_id = tool["tool_id"]
            _call(["call", f"{API}/tool-box/{box_id}/tool/{tool_id}", "-X", "POST", "-d",
                   json.dumps({"name": payload["name"], "description": payload["description"],
                               "metadata_type": "function", "function_input": payload}, ensure_ascii=False)])
        if tool is None or tool.get("status") != "enabled":
            _call(["tool", "enable", "--toolbox", box_id, tool_id])
        tool_ids[operation] = tool_id
    if box.get("status") != "published":
        _call(["toolbox", "publish", box_id])
    if kn_id:
        _call(["bkn", "capability", "attach", kn_id, "--box", box_id, "--tool", ",".join(tool_ids.values())])
    return {**preview, "box_id": box_id, "tool_ids": tool_ids}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--kn-id", help="Mount the functions to this knowledge network")
    args = parser.parse_args()
    print(json.dumps(run(apply=args.apply, kn_id=args.kn_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
