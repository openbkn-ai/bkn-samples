"""未关闭预测单数: 适用场景：统计某产品或全部产品的未关闭预测单数量。输入：可选产品编码。结果：默认返回未关闭张数与排除口径；传 report_grain=full 才返回预测单
ID 列表，不代表预测需求数量。"""

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
