"""生产计划齐套倒排: 适用场景：核查已有预测单或新客户需求能否按截止日交付。输入：已有预测单时只需预测单号和替代料策略；新增需求提供产品、数量、截止日和替代料策略。结果：先给成品
直发或生产计划模式，再给客户最早可用日期、客户延期天数、内部最大延迟、缺料和供应状态；Sample 默认业务日期为 2026-08-25。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_backward_plan


@tool
def backward_plan_tool(
    product: str | None = None,
    forecast_id: str | None = None,
    demand_end: str | None = None,
    demand_qty: float | None = None,
    business_date: str | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("backward_plan", query_object_instance, params)
    result = run_backward_plan(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
