"""BOM_Structure: Use case: BOM structure. Input: product, optional depth/alternates.
Result: summary counts and first-level mains; full returns paged rows."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_bom_list


@tool
def bom_list_tool(
    product: str | None = None,
    depth: int | None = None,
    include_substitute: bool | None = None,
    report_grain: str | None = None,
    page_size: int | None = None,
    offset: int | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("bom_list", query_object_instance, params)
    result = run_bom_list(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
