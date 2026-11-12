"""Machine scheduling on the platform: the two scheduled objects on datasets, one toolbox, mounted rules, two actions.

- Operations and maintenance work orders are what the scheduler changes, so their object types read
  datasets in the sample's catalog (the only writable source), loaded from the package's CSV.
- One toolbox holds four rule functions (工单齐套, 设备能力, 人员资质与班次, 换型提示; Workshop
  schedule rule tools) and the two adjust functions.
- The rule functions change nothing, so they are mounted on the network as functions (Q&A and Skills
  call them with execute_tool, the same code as the Gantt); only what changes objects is an action:
  "调整工序排程" / "调整维修工单", modify actions on their object types, inputs named like the fields.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

try:
    from installer.sample_logging import run as run_sample_command
except ImportError:
    # Older installers retain the original subprocess behavior.
    run_sample_command = subprocess.run

from function_bundle import SCHEDULED, build
from ownership_receipt import remember, require_owned

ROOT = Path(__file__).resolve().parents[1]
API = "/api/agent-operator-integration/v1"
BKN_API = "/api/bkn-backend/v1"
VEGA = "/api/vega-backend/v1"
RULES = ("work_order_kit_rule", "machine_capability_rule", "operator_shift_rule", "changeover_rule")
ADJUST = ("adjust_operation_schedule", "adjust_maintenance_work_order")
OPERATIONS = RULES + ADJUST

# operation -> ((en name, zh name), (en description, zh description))
CATALOG = {
    "work_order_kit_rule": (("Work order kit", "工单齐套"), (
        "Is the work order's material complete when its first open operation starts? Requirement = quantity × quantity_per × (1 + scrap), "
        "rounded up; available = issued + available stock (on hand − allocated, not the inspection hold) + open purchase orders expected "
        "by the start day and not overdue. Open work orders draw on the same stock in start order. A BOM revision that is not frozen "
        "also fails. Hard; related = operations of work orders competing for the same material; detail = material table.",
        "检查工单首道未完成工序开工时物料是否齐套：需求 = 数量 × 单耗 × (1 + 损耗率) 向上取整；可用 = 已发料 + 可用库存（在手 − 已分配，"
        "不含待检区）+ 开工日前预计到货、未逾期的采购余量。各未完工单按开工先后分用同一批库存；BOM 版本未冻结也不通过。"
        "不通过为硬约束；related 是争同一物料的工序；明细是物料表。")),
    "machine_capability_rule": (("Machine capability", "设备能力"), (
        "Is the planned machine's capability for the step's required capability qualified? Hard; detail = machine capability table.",
        "检查计划机台对工步所需能力的状态是否为合格。不合格为硬约束；明细是机台能力表。")),
    "operator_shift_rule": (("Operator qualification and shift", "人员资质与班次"), (
        "In the weekly shift covering the start day, is an active operator qualified (valid_to not before the start) rostered at the "
        "work centre? None is hard; fewer than the operations at the work centre on the same day is soft (related = those operations); "
        "detail = operator table.",
        "检查覆盖开工日的周班次里，该工作中心是否排有资质合格、未过期的在职操作员。没有为硬约束；人数少于同一天在该工作中心的工序数为软提示"
        "（related 是这些工序）；明细是人员表。")),
    "changeover_rule": (("Changeover", "换型提示"), (
        "Does the operation's setup class (from its step) differ from the previous operation on the same machine? Soft; related = the "
        "neighbouring operations.",
        "检查同一机台上按开工先后的前一道工序与本道的换型类别（取自工步）是否不同。不同为软提示；related 是相邻工序。")),
    "adjust_operation_schedule": (("Adjust operation schedule", "调整工序排程"), (
        "Move one operation that is not completed: planned machine (same work centre), planned start and planned end day. "
        "Without an end day the standard duration is used.",
        "调整一道未完成工序的计划机台（同一工作中心内）、计划开工日和计划完工日；只给开工日时按标准工期推算完工日。")),
    "adjust_maintenance_work_order": (("Adjust maintenance work order", "调整维修工单"), (
        "Move one maintenance work order that is not completed: planned start and end day. planned_date, the due day, is kept.",
        "调整一张未完成维护工单的计划开始日和计划结束日；应保养日 planned_date 不变。")),
}
RULE_USE = (
    "Schedule rule tool. tasks: operations to check, at most 200, e.g. [{\"key\":\"OP-2703-06-10\"}]; with only a key the stored "
    "planned machine and days are checked; add start, end (YYYY-MM-DD, end inclusive) and resource (machine ID) to try a change; an "
    "empty list checks every operation not started. Returns per task pass (null = not applicable), severity (hard or soft), text and "
    "related. Mounted on the network as a function: call it with execute_tool.",
    "排程规则工具。tasks：要检查的工序，一次最多 200 条，如 [{\"key\":\"OP-2703-06-10\"}]；只给 key 时按已存的计划机台和计划日期检查；"
    "带上 start、end（YYYY-MM-DD，含当天）和 resource（机台编号）可试算改排；传空列表检查全部未开工工序。返回每条的 pass（null 表示不适用）、"
    "severity（hard 或 soft）、text 和 related。函数直接挂载在知识网络上，用 execute_tool 调用。")
ADJUST_USE = (
    "Only the planned fields change. Check the move with the four schedule rules first; report the before and after values.",
    "只修改计划字段。改之前先用四个排程规则检查；回答时说明改前改后的值。")


def _input(name: str, kind: str, en: str, zh_text: str, zh: bool, required: bool = False) -> dict[str, Any]:
    return {"name": name, "type": kind, "required": required, "description": zh_text if zh else en}


def tool_inputs(operation: str, zh: bool) -> list[dict[str, Any]]:
    if operation in RULES:
        tasks = _input("tasks", "array", "Operations to check, at most 200: key (operation ID), optional start, end, resource, values.",
                       "要检查的工序，最多 200 条：key（工序编号），可带 start、end、resource、values。", zh)
        tasks["sub_parameters"] = [{"name": "items", "type": "object", "required": True,
                                    "description": "One task: key, start, end, resource, values." if not zh else "一条任务：key、start、end、resource、values。"}]
        return [tasks,
                _input("scenario", "object", "The scenario's edits; the tasks already carry them.", "方案改动（edits）；任务里已是改动后的值。", zh),
                _input("mode", "string", "Empty for a check; \"detail\" for one task's paged table.", "不传为检查；传 detail 取单条任务的分页明细。", zh),
                _input("task", "object", "With mode detail: the task.", "mode 为 detail 时的那条任务。", zh),
                _input("locale", "string", "zh-CN or en-US for the labels.", "标签语言：zh-CN 或 en-US。", zh),
                _input("query", "object", "With mode detail: group, keyOnly, search, offset, limit (default 50).",
                       "mode 为 detail 时：group、keyOnly、search、offset、limit（默认 50）。", zh)]
    if operation == "adjust_operation_schedule":
        return [_input("operation_id", "string", "Operation ID.", "工序编号。", zh, True),
                _input("planned_machine_id", "string", "Planned machine, in the operation's work centre.", "计划机台，须在工序的工作中心内。", zh),
                _input("planned_start_date", "string", "Planned start day YYYY-MM-DD.", "计划开工日 YYYY-MM-DD。", zh),
                _input("planned_end_date", "string", "Planned end day YYYY-MM-DD, inclusive.", "计划完工日 YYYY-MM-DD（含当天）。", zh)]
    return [_input("maintenance_work_order_id", "string", "Maintenance work order ID.", "维护工单编号。", zh, True),
            _input("planned_start_date", "string", "Planned start day YYYY-MM-DD.", "计划开始日 YYYY-MM-DD。", zh),
            _input("planned_end_date", "string", "Planned end day YYYY-MM-DD, inclusive.", "计划结束日 YYYY-MM-DD（含当天）。", zh)]


def is_zh() -> bool:
    return json.loads((ROOT / "model-contract.json").read_text(encoding="utf-8")).get("language") == "zh-cn"


def action_definitions(kn_id: str, box_id: str, tool_ids: dict[str, str], zh: bool) -> list[dict[str, Any]]:
    """Only what changes objects is an action: the two adjust functions, as modify actions on their objects."""
    i = 1 if zh else 0
    actions = []
    targets = {"adjust_operation_schedule": "manufacturing_operations", "adjust_maintenance_work_order": "maintenance_work_orders"}
    for op in ADJUST:
        (names, descriptions) = CATALOG[op]
        inputs = tool_inputs(op, zh)
        parameters = [{"name": inputs[0]["name"], "type": "string", "value_from": "property", "value": inputs[0]["name"],
                       "comment": inputs[0]["description"]}]
        parameters += [{"name": p["name"], "type": "string", "value_from": "input", "comment": p["description"]} for p in inputs[1:]]
        actions.append({"id": f"{kn_id}_{op}", "name": names[i], "branch": "main", "operation_config": {"type": "object"},
                        "object_type_id": targets[op], "action_type": "modify", "action_intent": "modify",
                        "action_source": {"type": "tool", "box_id": box_id, "tool_id": tool_ids[op]},
                        "parameters": parameters, "comment": descriptions[i] + "\n" + ADJUST_USE[i]})
    return actions


def box_name() -> str:
    sample = json.loads((ROOT / "sample.yaml").read_text(encoding="utf-8"))["metadata"]["name"]
    return "MANUFACTURING_" + sample.rsplit("industry-", 1)[1].replace("-", "_") + "_Schedule"


# --- datasets of the two scheduled objects ------------------------------------------------------------
def dataset_rows(table: str) -> list[dict[str, Any]]:
    fields = json.loads((ROOT / "model-contract.json").read_text(encoding="utf-8"))["object_types"][table]
    key = fields["primary_key"]
    rows = []
    with (ROOT / "data" / f"{table}.csv").open(encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row: dict[str, Any] = {"_id": raw[key]}
            for name, kind in fields["fields"].items():
                value = raw[name]
                if value == "":
                    continue
                row[name] = int(value) if kind == "integer" else (float(value) if kind == "decimal" else value)
            rows.append(row)
    return rows


def dataset_schema(table: str) -> list[dict[str, Any]]:
    fields = json.loads((ROOT / "model-contract.json").read_text(encoding="utf-8"))["object_types"][table]["fields"]
    return [{"name": name, "display_name": name, "type": kind, "description": ""} for name, kind in fields.items()]


def datasets(cli: Callable[..., Any], kn_id: str, catalog_id: str, apply: bool) -> dict[str, str]:
    """Bind each scheduled object to its own dataset in the sample's catalog; load the package rows once."""
    listed = cli("vega", "catalog", "resources", catalog_id, "--category", "dataset", "--limit", "-1")
    listed = listed if isinstance(listed, list) else next((listed[k] for k in ("entries", "data", "resources") if isinstance(listed.get(k), list)), [])
    out = {}
    for table in SCHEDULED:
        found = [r for r in listed if r.get("name") == table]
        if len(found) > 1:
            raise ValueError("ambiguous dataset " + table)
        if found:
            resource = found[0]["id"]
        else:
            if not apply:
                raise ValueError("missing dataset " + table)
            resource = cli("call", f"{VEGA}/resources", "-X", "POST", "-d", json.dumps(
                {"catalog_id": catalog_id, "name": table, "category": "dataset", "description": table,
                 "schema_definition": dataset_schema(table)}, ensure_ascii=False))["id"]
        if not apply:  # the platform hook checks every binding from the network export
            out[table] = resource
            continue
        obj = cli("bkn", "object-type", "get", kn_id, table)
        obj = (obj.get("entries") or [obj])[0] if isinstance(obj, dict) else obj[0]
        if (obj.get("data_source") or {}).get("id") != resource:
            obj["data_source"] = {"type": "resource", "id": resource}
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / (table + ".json")
                path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
                cli("bkn", "object-type", "update", kn_id, table, "--body-file", str(path))
        # Installing puts the package's schedule in place; a full replace by key is idempotent.
        rows = dataset_rows(table)
        answer = cli("call", f"{VEGA}/resources/{resource}/data", "-X", "PUT", "-d", json.dumps({"entries": rows}, ensure_ascii=False))
        results = answer.get("entries", []) if isinstance(answer, dict) else []
        if len(results) != len(rows) or any(int(r.get("status") or 0) >= 300 for r in results):
            raise ValueError("dataset load incomplete: " + table)
        out[table] = resource
    return out


# --- toolbox, functions, actions ------------------------------------------------------------------------
def run(cli: Callable[..., Any], kn_id: str, *, apply: bool, catalog_id: str) -> dict[str, Any]:
    zh = is_zh()
    bound = datasets(cli, kn_id, catalog_id, apply)
    name = box_name()
    boxes = cli("toolbox", "list", "--keyword", name, "--limit", "100")
    boxes = [b for b in (boxes.get("data") or boxes.get("entries") or []) if b.get("box_name") == name]
    if len(boxes) > 1:
        raise ValueError("ambiguous owned toolbox")
    if not boxes:
        if not apply:
            raise ValueError("missing owned toolbox")
        box = cli("call", API + "/tool-box", "-X", "POST", "-d", json.dumps({
            "box_name": name, "box_desc": "Machine scheduling rules and adjustments of the manufacturing sample",
            "box_category": "data_process", "metadata_type": "function", "source": "custom"}))
        remember("toolboxes", box["box_id"])
    else:
        box = boxes[0]
        require_owned("toolboxes", box["box_id"])
    bid = box["box_id"]
    listed = cli("tool", "list", "--toolbox", bid, "--all")
    tools = listed.get("tools") or listed.get("data") or listed.get("entries") or []
    tool_ids, hashes = {}, {}
    for op in OPERATIONS:
        code = build(op, kn_id)
        hashes[op] = hashlib.sha256(code.encode()).hexdigest()
        (names, descriptions) = CATALOG[op]
        found = next((t for t in tools if t.get("name") == op), None)
        body = {"name": op, "description": descriptions[1 if zh else 0], "script_type": "python", "code": code,
                "inputs": tool_inputs(op, zh),
                "outputs": [{"name": "result", "type": "object", "required": True,
                             "description": "results per task, a detail table, or the changed row"}]}
        if apply:
            if found:
                tid = found["tool_id"]
                cli("call", f"{API}/tool-box/{bid}/tool/{tid}", "-X", "POST", "-d", json.dumps(
                    {"name": op, "description": body["description"], "metadata_type": "function", "function_input": body}, ensure_ascii=False))
            else:
                tid = cli("call", f"{API}/tool-box/{bid}/tool", "-X", "POST", "-d", json.dumps(
                    {"metadata_type": "function", "function_input": body}, ensure_ascii=False))["success_ids"][0]
            cli("tool", "enable", "--toolbox", bid, tid)
        else:
            if not found:
                raise ValueError("missing function " + op)
            tid = found["tool_id"]
            saved = (cli("tool", "get", "--toolbox", bid, tid).get("metadata") or {}).get("function_content", {}).get("code")
            if saved != code:
                raise ValueError("published source differs " + op)
        tool_ids[op] = tid
    actions = action_definitions(kn_id, bid, tool_ids, zh)
    rules = [tool_ids[op] for op in RULES]
    if apply:
        if box.get("status") != "published":
            cli("toolbox", "publish", bid)
        # The rule functions change nothing: mounted on the network as functions (binding twice is a no-op).
        cli("bkn", "capability", "attach", kn_id, "--box", bid, "--tool", ",".join(rules))
        # The adjust functions change objects: modify actions; overwrite keeps a repeated install idempotent.
        cli("call", f"{BKN_API}/knowledge-networks/{kn_id}/action-types?import_mode=overwrite", "-X", "POST", "-d",
            json.dumps({"entries": actions}, ensure_ascii=False))
    else:
        mounted = cli("call", f"{BKN_API}/knowledge-networks/{kn_id}/capabilities?limit=1000")
        # Only explicit bindings count: entries derived from actions have no binding id and execute_tool ignores them.
        mounted = {str(c.get("capability_id")) for c in (mounted.get("entries") or []) if c.get("id")} if isinstance(mounted, dict) else set()
        if not set(rules) <= mounted:
            raise ValueError("rule function not mounted: " + ", ".join(op for op in RULES if tool_ids[op] not in mounted))
        listed = cli("bkn", "action-type", "list", kn_id)
        listed = listed if isinstance(listed, list) else (listed.get("entries") or listed.get("data") or [])
        present = {(a.get("id"), (a.get("action_source") or {}).get("tool_id")) for a in listed}
        missing = [a["id"] for a in actions if (a["id"], a["action_source"]["tool_id"]) not in present]
        if missing:
            raise ValueError("missing action " + ", ".join(missing))
    return {"datasets": bound, "toolbox_id": bid, "tool_ids": tool_ids, "action_ids": [a["id"] for a in actions],
            "mounted_tool_ids": rules, "source_sha256": hashes}


__all__ = ["ADJUST", "CATALOG", "OPERATIONS", "RULES", "action_definitions", "box_name", "dataset_rows", "run", "tool_inputs"]
