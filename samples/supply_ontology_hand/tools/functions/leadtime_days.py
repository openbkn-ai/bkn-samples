"""标准交期: 适用场景：查询单个物料的标准提前期。输入：物料编码。结果：leadtime_days、caliber（purchase/production）、material_a
ttribute、source_field、unit 及正式物料 object_type_id。外购/委外取采购固定提前期，其他属性取生产固定提前期；缺失属性沿用生产默认并标记
attribute_missing，不代表已确认物料属性。"""

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
