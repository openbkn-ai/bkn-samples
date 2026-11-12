"""Run the machine-scheduling functions inside the Function sandbox.

The functions read the tables they need from the knowledge network (``sandbox_sdk.bkn``), and the
two adjust functions write the changed row back into the object's dataset (``bkn_osdk.call``, a
Vega dataset bulk PUT). Anything incomplete raises, so a rule tool's tasks are marked "not
checked" instead of passing.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

import machine_schedule as ms

PAGE_SIZE = 500
MAX_ROWS = 20_000
# Set by the bundle: the network, its language and the field types of the two scheduled objects.
KN_ID = ""
LANGUAGE = "zh"
FIELDS: dict[str, dict[str, str]] = {}
KEYS = {"manufacturing_operations": "operation_id", "maintenance_work_orders": "maintenance_work_order_id"}


def _rows(page: Mapping[str, Any]) -> list[dict[str, Any]]:
    for key in ("datas", "data", "entries"):
        if isinstance(page.get(key), list):
            return [dict(r) for r in page[key] if isinstance(r, Mapping)]
    raise ValueError("object query returned no rows field")


def read_table(query: Callable[..., Any], table: str, condition: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Every row of an object type, page by page; fails on a partial or inconsistent read."""
    rows, seen, total = [], set(), None
    while True:
        request = {"kn_id": KN_ID, "ot_id": table, "limit": PAGE_SIZE, "offset": len(rows)}
        if condition:
            request["condition"] = condition
        page = query(**request)
        if not isinstance(page, Mapping):
            raise ValueError("invalid object page: " + table)
        if page.get("status") in ("partial", "failed", "error", "incomplete") or page.get("partial") or page.get("errors"):
            raise ValueError("incomplete object query: " + table)
        count = page.get("total_count")
        if count is not None:
            if isinstance(count, bool) or not isinstance(count, int) or (total is not None and count != total):
                raise ValueError("invalid or changing total_count: " + table)
            total = count
        batch = _rows(page)
        for row in batch:
            marker = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
            if marker in seen:
                raise ValueError("repeated row prevents a complete read: " + table)
            seen.add(marker)
        rows += batch
        if len(rows) > MAX_ROWS:
            raise ValueError("too many rows: " + table)
        if total is not None and len(rows) >= total:
            if len(rows) > total:
                raise ValueError("more rows than total_count: " + table)
            return rows
        if len(batch) < PAGE_SIZE and page.get("has_more") is not True:
            if total is not None and len(rows) < total:
                raise ValueError("object query ended early: " + table)
            return rows


def reader(sdk_query: Callable[..., Any], call: Callable[..., Any] | None) -> Callable[..., Any]:
    """The SDK's object query; without a Context Loader interaction (a Workshop rule-tool call through the
    toolbox) the SDK refuses, so the same query goes to ontology-query directly as the caller."""
    direct = {"on": False}

    def rest(kn_id: str, ot_id: str, limit: int, offset: int, condition: Any = None) -> Any:
        body = {"limit": limit, "offset": offset, "need_total": True, **({"condition": condition} if condition else {})}
        return call(f"/api/ontology-query/v1/knowledge-networks/{kn_id}/object-types/{ot_id}", method="POST", body=body,
                    headers={"X-HTTP-Method-Override": "GET"})

    def query(**request: Any) -> Any:
        if direct["on"]:
            return rest(**request)
        try:
            return sdk_query(**request)
        except Exception as error:  # the SDK raises its own ToolError
            text = str(error)
            if call is None or not ("conversation_required" in text or "bkn_context" in text):
                raise
            direct["on"] = True
            return rest(**request)
    return query


def load(query: Callable[..., Any], tables: tuple[str, ...]) -> dict[str, list[dict[str, Any]]]:
    return {table: read_table(query, table) for table in tables}


def rule(name: str, query: Callable[..., Any], *, call: Callable[..., Any] | None = None, tasks: Any = None, scenario: Any = None, mode: Any = None,
         task: Any = None, locale: Any = None, detail_query: Any = None) -> dict[str, Any]:
    """A rule tool call: batch check, or ``mode="detail"`` for one task's table."""
    tables = load(reader(query, call), ms.tables_for(name))
    if str(mode or "").strip() == "detail":
        return ms.detail(name, tables, task, scenario, language=LANGUAGE, locale=locale, query=detail_query)
    return ms.check(name, tables, tasks, scenario, language=LANGUAGE, locale=locale)


def typed(table: str, row: Mapping[str, Any]) -> dict[str, Any]:
    """A dataset document of the object: its fields only, dates as days, numbers as numbers, no empty values."""
    out: dict[str, Any] = {}
    for field, kind in FIELDS[table].items():
        value = row.get(field)
        if value in (None, ""):
            continue
        if kind == "date":
            value = ms.day(value)
        elif kind == "integer":
            value = int(ms.num(value))
        elif kind == "decimal":
            value = ms.show(ms.num(value))
        else:
            value = str(value)
        out[field] = value
    return out


def dataset_of(call: Callable[..., Any], table: str) -> str:
    definition = call(f"/api/bkn-backend/v1/knowledge-networks/{KN_ID}/object-types/{table}")
    entries = definition.get("entries") if isinstance(definition, Mapping) else None
    source = ((entries[0] if entries else definition) or {}).get("data_source") or {}
    if source.get("type") != "resource" or not source.get("id"):
        raise ValueError(f"{table} is not bound to a dataset")
    return str(source["id"])


def write(call: Callable[..., Any], table: str, row: Mapping[str, Any]) -> None:
    document = typed(table, row)
    resource = dataset_of(call, table)
    answer = call(f"/api/vega-backend/v1/resources/{resource}/data", method="PUT",
                  body={"entries": [{"_id": document[KEYS[table]], **document}]})
    results = answer.get("entries") if isinstance(answer, Mapping) else None
    if not isinstance(results, list) or len(results) != 1 or int(results[0].get("status") or 0) >= 300:
        raise ValueError(f"dataset write was not confirmed: {results!r}")


def adjust_operation(query: Callable[..., Any], call: Callable[..., Any], params: Mapping[str, Any]) -> dict[str, Any]:
    """调整工序排程: move one operation (planned machine, start, end); returns the row before and after."""
    tables = load(reader(query, call), ("manufacturing_operations", "process_steps", "production_orders", "production_machines"))
    changed = ms.adjust_operation(ms.Facts(tables, language=LANGUAGE), params)
    write(call, "manufacturing_operations", changed["row"])
    return {"operation": typed("manufacturing_operations", changed["row"]), "previous": changed["previous"]}


def adjust_maintenance(query: Callable[..., Any], call: Callable[..., Any], params: Mapping[str, Any]) -> dict[str, Any]:
    """调整维修工单: move one maintenance work order's planned days; the due day stays."""
    changed = ms.adjust_maintenance(read_table(reader(query, call), "maintenance_work_orders"), params, language=LANGUAGE)
    write(call, "maintenance_work_orders", changed["row"])
    return {"maintenance_work_order": typed("maintenance_work_orders", changed["row"]), "previous": changed["previous"]}


__all__ = ["adjust_maintenance", "adjust_operation", "load", "read_table", "reader", "rule", "typed"]
