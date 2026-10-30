"""Single source of truth for Agent-facing supply calculation Tool guidance."""

from __future__ import annotations

EXECUTION_USE_RULE = (
    '通过 execute_tool 直接调用；从发现结果原样复制 toolbox_id=owner_id、tool_id=capability_id，不重构 ID。'
    '检查 body.exit_code 和 result，HTTP 200 不等于计算成功。'
    '只查数、汇总、追关系的问题用 Cypher，不要调用函数。'
)


def _spec(name: str, operation: str, description: str, *, use_when: str, do_not_use_when: str,
          minimum_business_inputs: list[str]) -> dict[str, object]:
    return {
        "name": name,
        "operation": operation,
        "description": description,
        "use_rule": EXECUTION_USE_RULE,
        "use_when": use_when,
        "do_not_use_when": do_not_use_when,
        "minimum_business_inputs": minimum_business_inputs,
    }


FUNCTION_CATALOG = {
    "build_capacity": _spec(
        "产品可做数量与可承诺量",
        "build_capacity",
        "按 BOM 逐层净扣，算每个产品各自的成品库存、还能生产的最大套数、已签约欠货、可承诺量（成品+可做−欠货），"
        "以及再多做一套时卡住的物料。默认只用现有可用库存、全仓、不用替代料；"
        "传 need_by 计入该日前按交期到货的在途，传 chase_overdue_po=true 计入逾期在途。",
        use_when="问某个或某几个产品现在能做多少、能卖多少、还能接多少新单、被哪颗料卡住，或某日前在途到货后能多做多少。"
                 "几个产品要一起看时一次传入 products，不要逐个调用。",
        do_not_use_when="只问库存、欠货、预测、在途数量或 BOM 清单时用 Cypher。",
        minimum_business_inputs=["products"],
    ),
    "demand_coverage": _spec(
        "需求齐套与缺料",
        "demand_coverage",
        "按数组顺序在同一库存池上逐条评估需求：先用成品，再按 BOM 逐层净扣，返回每条需求能否满足、"
        "需生产套数和最底层缺料数量。reserve_signed_backlog=true 先按承诺交期扣掉这些产品的已签约欠货；"
        "use_finished_goods=false 表示排生产工单、不用成品。在途与替代料参数同可做数量函数。",
        use_when="问一张或几张需求（新单、欠单、计划工单）够不够、缺什么料、缺多少，或多单同时来时怎么分库存。",
        do_not_use_when="只问最多能做多少套时用可做数量函数。",
        minimum_business_inputs=["demands"],
    ),
}


def native_tool_description() -> str:
    """Return a concise description of the native Function collection."""
    operations = "；".join(f"{operation}（{spec['name']}）" for operation, spec in FUNCTION_CATALOG.items())
    return (
        f"供应链计划计算函数：{operations}。"
        "函数在运行时通过 sandbox_sdk.bkn 读取已绑定的知识网络；未传 business_date 时按 2026-08-25 计算。"
    )


def native_operation_description() -> str:
    return "可用具名函数：" + "、".join(FUNCTION_CATALOG)


__all__ = ["FUNCTION_CATALOG", "native_operation_description", "native_tool_description"]
