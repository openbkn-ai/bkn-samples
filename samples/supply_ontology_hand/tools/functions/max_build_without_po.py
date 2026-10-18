"""无需采购最大可产: 适用场景：判断不新增采购时还能生产多少。输入：产品编码、替代料策略，仓范围默认全仓，显式范围优先。结果：默认返回策略支持再制造量和瓶颈料；传
report_grain=full 才返回全部物料约束；不含成品库存和在途。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_max_build_without_po


@tool
def max_build_without_po_tool(
    product: str | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("max_build_without_po", query_object_instance, params)
    result = run_max_build_without_po(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
