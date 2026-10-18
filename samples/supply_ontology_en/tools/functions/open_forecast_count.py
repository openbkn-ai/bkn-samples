"""Open_Forecast_Count: Use case: open forecast count. Input: optional product. Result:
record count and exclusions; full adds IDs. Not forecast demand quantity."""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_open_forecast_count


@tool
def open_forecast_count_tool(
    product_code: str | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("open_forecast_count", query_object_instance, params)
    result = run_open_forecast_count(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
