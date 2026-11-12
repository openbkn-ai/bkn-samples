"""Schedule-Gantt rule tools for kit-schedule plans: kit check and line can build.

The rule-tool contract: input ``{tasks: [{key, start, end, resource, values}], scenario: {edits}}``
(at most 200 tasks; the tasks already carry the scenario's changes); output ``{results: [{key, pass,
severity, text, related, at?, counts?, detail?}]}``. The kit check also answers a detail call for one
task, ``{mode: "detail", task, scenario, locale, query: {group?, keyOnly?, search?, offset, limit}}``,
with a paged table of the plan's short materials. Both check the tasks against the network's other
active plans (with the scenario's edits of those plans applied), so they agree with each other.

The Functions read the facts they need through ``sandbox_sdk.bkn``; anything they cannot check raises,
so the caller marks the tasks "not checked" instead of passing them.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from fn import DEFAULT_BUSINESS_DATE
from fn.kitrules import CANCELLED, _labels, check_tasks, demands_of, kit_detail, kit_rule, line_rule, overlay, task_fields
from fn.read_complete import read_complete
from managed_execution import KN_ID, _in, _page_rows, load_bkn_rows

OT_FORECAST = f"{KN_ID}_forecast"
OT_MATERIAL = f"{KN_ID}_material"
OT_LINE = f"{KN_ID}_line"
OT_PLAN = f"{KN_ID}_kitplan"
OT_PRODUCT = f"{KN_ID}_product"
OT_WORK = f"{KN_ID}_mps"
PLAN_FIELDS = ("bill_no", "product_code", "line_code", "planned_start", "planned_finish", "plan_status")
CHUNK = 500


def tool_query(sdk_query: Callable[..., Mapping[str, Any]], call: Callable[..., Any]) -> Callable[..., Mapping[str, Any]]:
    """Object reads for a rule tool. The schedule Gantt calls it through the toolbox proxy, outside a Context Loader
    interaction, where the SDK reader refuses (``conversation_required``); the ontology query API then answers the
    same object query as the caller. Inside an interaction (an action, Q&A) the SDK reader is used."""
    state = {"sdk": True}

    def direct(kn_id: str, ot_id: str, condition: Any = None, limit: int = 500, offset: int = 0, **_: Any) -> Mapping[str, Any]:
        body: dict[str, Any] = {"limit": limit, "offset": offset, "need_total": True}
        if condition:
            body["condition"] = condition
        return call(f"/api/ontology-query/v1/knowledge-networks/{kn_id}/object-types/{ot_id}", method="POST", body=body,
                    headers={"X-HTTP-Method-Override": "GET"})

    def query(**request: Any) -> Mapping[str, Any]:
        if state["sdk"]:
            try:
                return sdk_query(**request)
            except Exception as error:  # the SDK raises its own error types
                if "conversation_required" not in str(error) and "bkn_context" not in str(error):
                    raise
                state["sdk"] = False
        request.pop("search_after", None)
        return direct(**request)
    return query


def _reader(query: Callable[..., Mapping[str, Any]]):
    def read(ot_id: str, field: str | None = None, values: list[str] | None = None) -> list[dict[str, Any]]:
        if field is None:
            return read_complete(query, {"kn_id": KN_ID, "ot_id": ot_id}, _page_rows, page_size=500, max_rows=50_000)
        rows = []
        for at in range(0, len(values or []), CHUNK):
            rows += read_complete(query, {"kn_id": KN_ID, "ot_id": ot_id, "condition": _in(field, values[at:at + CHUNK])},
                                  _page_rows, page_size=500, max_rows=50_000)
        return rows
    return read


def _forecasts(read, tasks) -> list[dict[str, Any]]:
    bills = sorted({task_fields(t)["bill"] for t in tasks} - {""})
    return read(OT_FORECAST, "billno", bills) if bills else []


def _facts(read, query, tasks, business_date):
    forecasts = _forecasts(read, tasks)
    demands = [d for t in tasks for d in demands_of(task_fields(t), forecasts)]
    bills = sorted({str(r.get("billno")) for r in forecasts})
    # Production orders of these forecasts: a started one has drawn its plan's materials.
    rows: dict[str, list[dict[str, Any]]] = {"forecast": forecasts,
                                             "work_order": read(OT_WORK, "sourcebillnumber", bills) if bills else []}
    materials: dict[str, dict[str, Any]] = {}
    if demands:
        starts = [task_fields(t)["start"] for t in tasks if task_fields(t)["start"]]
        rows.update(load_bkn_rows("demand_coverage", query, {"demands": demands, "need_by": max(starts or [business_date]),
                                                             "reserve_signed_backlog": True}))
        codes = sorted({str(r.get("material_code")) for r in rows["bom"]})
        materials = {str(m["material_code"]): m for m in read(OT_MATERIAL, "material_code", codes)}
    return rows, materials


def kit_check(tasks: Any, query: Callable[..., Mapping[str, Any]], *, scenario: Any = None,
              business_date: str = DEFAULT_BUSINESS_DATE, locale: str | None = None) -> dict[str, Any]:
    """The tasks sent, checked with the network's other active plans, as the detail is."""
    tasks = check_tasks(tasks, locale)
    read = _reader(query)
    others = _active_plans(read, scenario)
    rows, materials = _facts(read, query, overlay(others, tasks), business_date)
    return {"results": kit_rule(tasks, rows, materials=materials, business_date=business_date, locale=locale,
                                others=others)}


def _active_plans(read, scenario: Any) -> list[dict[str, Any]]:
    """The network's active plans as tasks, with the scenario's edits of those plans applied."""
    edits = {}
    for edit in (scenario or {}).get("edits") or [] if isinstance(scenario, Mapping) else []:
        params = edit.get("params") if isinstance(edit, Mapping) else None
        if isinstance(params, Mapping) and edit.get("key"):
            edits.setdefault(str(edit["key"]), {}).update({k: v for k, v in params.items() if k in PLAN_FIELDS})
    tasks = []
    for plan in read(OT_PLAN):
        key = str(plan.get("plan_id") or "")
        values = {**plan, **edits.get(key, {})}
        if key and values.get("plan_status") != CANCELLED:
            tasks.append({"key": key, "start": values.get("planned_start"), "end": values.get("planned_finish"),
                          "resource": values.get("line_code"), "values": values})
    return tasks


def kit_check_detail(task: Any, query: Callable[..., Mapping[str, Any]], *, scenario: Any = None, locale: str | None = None,
                     page: Mapping[str, Any] | None = None, business_date: str = DEFAULT_BUSINESS_DATE) -> dict[str, Any]:
    if not isinstance(task, Mapping) or not task.get("key"):
        raise ValueError(_labels(locale)["bad_task"])
    read = _reader(query)
    others = _active_plans(read, scenario)
    rows, materials = _facts(read, query, overlay(others, [task]), business_date)
    product = task_fields(task)["product"]
    names = {str(p.get("material_number")): str(p.get("material_name") or "")
             for p in (read(OT_PRODUCT, "material_number", [product]) if product else [])}
    return kit_detail(task, others, rows, materials=materials, products=names, business_date=business_date,
                      locale=locale, query=page, kn_id=KN_ID)


def line_check(tasks: Any, query: Callable[..., Mapping[str, Any]]) -> dict[str, Any]:
    tasks = check_tasks(tasks)
    read = _reader(query)
    forecasts = _forecasts(read, tasks)
    products = sorted({str(r["material_number"]) for r in forecasts} | {task_fields(t)["product"] for t in tasks} - {""})
    product_lines = {str(m["material_code"]): str(m.get("huid_productline_name") or "")
                     for m in (read(OT_MATERIAL, "material_code", products) if products else [])}
    lines = {str(l["line_code"]): l for l in read(OT_LINE)}
    return {"results": line_rule(tasks, forecasts=forecasts, lines=lines, product_lines=product_lines)}


__all__ = ["kit_check", "kit_check_detail", "line_check", "tool_query"]
