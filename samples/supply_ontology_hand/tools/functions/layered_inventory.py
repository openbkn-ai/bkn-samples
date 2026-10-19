"""子料分层库存: 适用场景：查看产品 BOM 子料在指定仓范围的可用库存。输入：产品编码，可选层数和仓范围。结果：各层子料、可用量、占用展示和实际仓范围。"""

from __future__ import annotations

from bkn_osdk.kn import query_object_instance
from sandbox_sdk import tool

from fn.snapshot import build_snapshot
from managed_execution import KN_ID, load_bkn_rows, run_layered_inventory


@tool
def layered_inventory_tool(
    product: str | None = None,
    depth: int | None = None,
    warehouse_scope: str | None = None,
    include_substitute: bool | None = None,
) -> dict:
    params = {name: value for name, value in locals().items() if value is not None}
    rows = load_bkn_rows("layered_inventory", query_object_instance, params)
    result = run_layered_inventory(build_snapshot(dict(rows)), rows, params)
    result["data_source"] = {"knowledge_network_id": KN_ID, "loaded_datasets": list(rows)}
    return result
