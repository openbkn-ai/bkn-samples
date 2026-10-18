"""BOM_Stock: Use case: component stock. Input: product, optional depth/scope. Result: BOM
levels, available stock and resolved scope; repeated positions share stock."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_layered_inventory


@tool
def layered_inventory_tool(
    product: str | None = None,
    depth: int | None = None,
    warehouse_scope: str | None = None,
    include_substitute: bool | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("layered_inventory", query_object_instance, params)
    result = run_layered_inventory(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
