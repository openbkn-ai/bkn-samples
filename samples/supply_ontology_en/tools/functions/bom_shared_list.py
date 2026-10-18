"""Shared_BOM: Use case: shared BOMs. Input: at least two products, optional
depth/alternates. Result: shared component structure without stock or allocation
analysis."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_bom_shared_list


@tool
def bom_shared_list_tool(
    products: list | None = None,
    depth: int | None = None,
    include_substitute: bool | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("bom_shared_list", query_object_instance, params)
    result = run_bom_shared_list(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
