"""共用料与多需求争用: 适用场景：判断多条需求同时承接时的共用物料争用。输入：至少两条产品与数量需求，数组顺序代表扣减优先级。结果：默认返回逐单满足状态和缺料清单；传
report_grain=full 才返回逐料分配和完整剩余池。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_shared_contention


@tool
def shared_contention_tool(
    demands: list | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
    report_grain: str | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("shared_contention", query_object_instance, params)
    result = run_shared_contention(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
