"""Shared_Demand_Allocation: Use case: shared stock allocation. Input: ordered demands,
explicit alternate policy, optional scope (all). Result: per-demand coverage and
shortages; full adds allocations and remaining pool."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_shared_contention


@tool
def shared_contention_tool(
    demands: list | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("shared_contention", query_object_instance, params)
    result = run_shared_contention(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
