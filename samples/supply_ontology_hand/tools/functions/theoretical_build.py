"""理论可产: 适用场景：判断现有生产物料最多可制造多少成品。输入：产品编码、替代料策略，可选生产仓范围。结果：默认返回理论可产量和瓶颈料；传 report_grain=full
才返回全部物料约束；不含成品库存和在途。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_theoretical_build


@tool
def theoretical_build_tool(
    product: str | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("theoretical_build", query_object_instance, params)
    result = run_theoretical_build(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
