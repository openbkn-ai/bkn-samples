"""Lead_Time: Use case: standard lead time. Input: material_code. Result: leadtime_days,
purchase/production caliber, material type, source field and unit; missing type keeps
the marked production default."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_leadtime_days


@tool
def leadtime_days_tool(
    material_code: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("leadtime_days", query_object_instance, params)
    result = run_leadtime_days(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
