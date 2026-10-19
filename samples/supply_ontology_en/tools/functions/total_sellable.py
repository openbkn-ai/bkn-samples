"""Total_Sellable: Use case: current sellable capacity. Input: product, explicit alternate
policy, optional scopes (all). Result: finished stock, manufacturing capacity and total
sellable; no incoming supply."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_total_sellable


@tool
def total_sellable_tool(
    product: str | None = None,
    production_scope: str | None = None,
    finished_goods_scope: str | None = None,
    substitute_enabled: bool | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("total_sellable", query_object_instance, params)
    result = run_total_sellable(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
