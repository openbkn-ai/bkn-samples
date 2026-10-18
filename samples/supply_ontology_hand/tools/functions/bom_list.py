"""BOM清单: 适用场景：查看产品 BOM 结构、层级和单耗。输入：产品编码，可选层数和是否包含替代料。结果：默认返回结构统计和一级主料；明确要求明细时才分页返回。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_bom_list


@tool
def bom_list_tool(
    product: str | None = None,
    depth: int | None = None,
    include_substitute: bool | None = None,
    report_grain: str | None = None,
    page_size: int | None = None,
    offset: int | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("bom_list", query_object_instance, params)
    result = run_bom_list(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
