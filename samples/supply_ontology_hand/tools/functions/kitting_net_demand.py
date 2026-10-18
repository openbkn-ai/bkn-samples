"""要X套净需求与齐套:
适用场景：判断指定数量是否齐套并找出缺料。输入：产品编码、需求套数、替代料策略，可选仓范围。结果：默认返回齐套结论、全部缺料清单及每项按当前需求快照建议补货量；传
report_grain=full 才返回全部物料明细。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_kitting_net_demand


@tool
def kitting_net_demand_tool(
    product: str | None = None,
    qty: float | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("kitting_net_demand", query_object_instance, params)
    result = run_kitting_net_demand(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
