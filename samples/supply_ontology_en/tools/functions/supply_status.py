"""Supply_Status: Use case: dated material coverage. Input: material, need date, gross
quantity, business date, optional scope (all). Result: on-time coverage/shortage and
stock/net PO evidence; excludes overdue, undated and closed POs."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_supply_status


@tool
def supply_status_tool(
    material_code: str | None = None,
    due_date: str | None = None,
    gross_requirement: float | None = None,
    warehouse_scope: str | None = None,
    child_short: bool | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("supply_status", query_object_instance, params)
    result = run_supply_status(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
