"""供应状态诊断: 适用场景：在倒排中已有到位日和毛需求时诊断单料供应状态。输入：物料编码、到位日、毛需求、business_date，可选仓范围（默认全仓）。结果：on_time
_covered、on_time_shortage_qty、按期库存/PO净未收数量及逐行日期证据；到货日晚于业务日且不晚于需要日的未关闭PO才计按期供给，过期和无日期PO不计
已确认覆盖。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_supply_status


@tool
def supply_status_tool(
    material_code: str | None = None,
    due_date: str | None = None,
    gross_requirement: float | None = None,
    warehouse_scope: str | None = None,
    child_short: bool | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("supply_status", query_object_instance, params)
    result = run_supply_status(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
