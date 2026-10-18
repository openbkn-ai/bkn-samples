"""Backward_Plan: Use case: deadline coverage. Input: forecast ID and alternate policy, or
product/quantity/deadline/policy. Result: direct-stock or net production plan,
customer/internal delays and evidence. Default business date: 2026-08-25."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_backward_plan


@tool
def backward_plan_tool(
    product: str | None = None,
    forecast_id: str | None = None,
    demand_end: str | None = None,
    demand_qty: float | None = None,
    business_date: str | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("backward_plan", query_object_instance, params)
    result = run_backward_plan(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
