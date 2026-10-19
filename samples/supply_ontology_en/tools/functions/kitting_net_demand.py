"""Demand_Coverage: Use case: fixed demand. Input: product, quantity, explicit alternate
policy, optional scope (all). Result: coverage, all shortages and suggested
replenishment; finished/component stock first, no POs."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_kitting_net_demand


@tool
def kitting_net_demand_tool(
    product: str | None = None,
    qty: float | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("kitting_net_demand", query_object_instance, params)
    result = run_kitting_net_demand(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
