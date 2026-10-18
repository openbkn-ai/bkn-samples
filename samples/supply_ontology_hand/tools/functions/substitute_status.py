"""替代料状态: 适用场景：确认产品或物料是否存在替代料及候选料库存。输入：产品编码或物料编码（二选一），可选仓范围和替代料策略。结果：替代组、候选料、可用量和策略状态。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_substitute_status


@tool
def substitute_status_tool(
    product: str | None = None,
    material_code: str | None = None,
    warehouse_scope: str | None = None,
    substitute_enabled: bool | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("substitute_status", query_object_instance, params)
    result = run_substitute_status(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
