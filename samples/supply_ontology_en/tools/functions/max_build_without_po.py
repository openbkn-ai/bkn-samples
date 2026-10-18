"""Stock_Only_Capacity: Use case: no-purchase manufacturing. Input: product, explicit
alternate policy, optional scope (all). Result: deterministic capacity and bottlenecks,
excluding finished goods and incoming supply."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_max_build_without_po


@tool
def max_build_without_po_tool(
    product: str | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("max_build_without_po", query_object_instance, params)
    result = run_max_build_without_po(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
