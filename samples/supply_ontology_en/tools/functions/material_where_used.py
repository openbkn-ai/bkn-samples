"""Where_Used: Use case: which products use a material. Input: material_code. Result:
affected_product_count and products, including alternate branches by default; full adds
BOM paths."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_material_where_used


@tool
def material_where_used_tool(
    material_code: str | None = None,
    include_substitute: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("material_where_used", query_object_instance, params)
    result = run_material_where_used(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
