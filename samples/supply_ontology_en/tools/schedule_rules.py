"""Schedule-Gantt rule tools for kit-schedule plans: kit check and line can build.

The rule-tool contract: input ``{tasks: [{key, start, end, resource, values}], scenario: {edits}}``
(at most 200 tasks; the tasks already carry the scenario's changes); output ``{results: [{key, pass,
severity, text, related}]}``. The Functions read the facts they need through ``sandbox_sdk.bkn``;
anything they cannot check raises, so the caller marks the tasks "not checked" instead of passing them.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from fn import DEFAULT_BUSINESS_DATE
from fn.kitrules import check_tasks, demands_of, kit_rule, line_rule, task_fields
from fn.read_complete import read_complete
from managed_execution import KN_ID, _in, _page_rows, load_bkn_rows

OT_FORECAST = f"{KN_ID}_forecast"
OT_MATERIAL = f"{KN_ID}_material"
OT_LINE = f"{KN_ID}_line"
CHUNK = 500


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


def kit_check(tasks: Any, query: Callable[..., Mapping[str, Any]], *, business_date: str = DEFAULT_BUSINESS_DATE) -> dict[str, Any]:
    tasks = check_tasks(tasks)
    read = _reader(query)
    forecasts = _forecasts(read, tasks)
    demands = [d for t in tasks for d in demands_of(task_fields(t), forecasts)]
    rows: dict[str, list[dict[str, Any]]] = {"forecast": forecasts}
    materials: dict[str, dict[str, Any]] = {}
    if demands:
        starts = [task_fields(t)["start"] for t in tasks if task_fields(t)["start"]]
        rows.update(load_bkn_rows("demand_coverage", query, {"demands": demands, "need_by": max(starts or [business_date]),
                                                             "reserve_signed_backlog": True}))
        codes = sorted({str(r.get("material_code")) for r in rows["bom"]})
        materials = {str(m["material_code"]): m for m in read(OT_MATERIAL, "material_code", codes)}
    return {"results": kit_rule(tasks, rows, materials=materials, business_date=business_date)}


def line_check(tasks: Any, query: Callable[..., Mapping[str, Any]]) -> dict[str, Any]:
    tasks = check_tasks(tasks)
    read = _reader(query)
    forecasts = _forecasts(read, tasks)
    products = sorted({str(r["material_number"]) for r in forecasts} | {task_fields(t)["product"] for t in tasks} - {""})
    product_lines = {str(m["material_code"]): str(m.get("huid_productline_name") or "")
                     for m in (read(OT_MATERIAL, "material_code", products) if products else [])}
    lines = {str(l["line_code"]): l for l in read(OT_LINE)}
    return {"results": line_rule(tasks, forecasts=forecasts, lines=lines, product_lines=product_lines)}


__all__ = ["kit_check", "line_check"]
