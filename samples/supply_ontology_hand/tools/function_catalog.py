"""Single source of truth for Agent-facing supply calculation Tool guidance."""

from __future__ import annotations

EXECUTION_USE_RULE = (
    '函数已挂载到知识网络，通过 execute_tool 直接调用；从发现结果原样复制 toolbox_id=owner_id、tool_id=capability_id，不重构 ID。'
    '替代料、仓范围、需求日期、逾期在途等是业务假设，用户没说时按说明里的默认值显式传入，并在回答里说明。'
    '检查 body.exit_code 和 result，HTTP 200 不等于计算成功。只查数、汇总、追关系的问题用 Cypher，不要调用函数。'
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


KIT_SCHEDULE = {
    "name": "齐套排产",
    "operation": "kit_schedule",
    "description": "把一张需求预测单（整单）或其中一个产品排到产线上，按计划开工日检查物料是否齐套"
                   "（先保已签约欠货，不动成品，只算开工前按期到货的在途），结果记到齐套排产计划，不改预测单。"
                   "同一张单的同一产品只保留一条有效计划：再次排产就更新这条计划并记一次改期，取消后可以重新排产。",
    # Agents reach it only through the three plan actions; their inputs are described on each parameter.
    "use_rule": "由建立、调整、取消齐套排产计划三个行动使用，不单独调用；查已排计划和齐套结论用知识网络查询。",
}
# Calling details (tasks, detail mode, paging) are on the tool parameters; this text is shown to business users.
RULE_USE = "排程甘特图检查计划时使用，问答里检查已排计划时也可以用；一次最多检查 200 条计划。"
SCHEDULE_RULES = {
    "kit_check_rule": {
        "name": "齐套检查",
        "description": "检查计划开工时物料是否齐套：先保已签约欠货，再按已确认、已排的顺序和开工先后分配现有库存与按期到货的在途。"
                       "缺料时指出关键物料、缺口和预计到货；还没下采购的物料按采购提前期估算到货日。"
                       "开工早于最早可开工日的计划不能采用。选中一条计划可以查看缺料明细。",
        "use_rule": RULE_USE,
    },
    "line_check_rule": {
        "name": "产线可生产",
        "description": "检查计划排到的产线能否生产这些产品：产品所属的产品线要在产线的可生产产品线之内，整单逐个产品检查；"
                       "排到工厂或不存在的产线也不通过，这样的计划不能采用。",
        "use_rule": RULE_USE,
    },
}
KIT_PLAN_ACTIONS = {
    "create": ("建立齐套排产计划", "add",
               "为一张需求预测单（整单）或其中一个产品建立齐套排产计划，并记录计划开工时的齐套结论。"
               "这张单的这个产品已有有效计划时，改为更新那条计划，不会重复建立。"),
    "adjust": ("调整齐套排产计划", "modify",
               "对选中的计划改产线、计划开工或计划完工，并重新检查齐套；计划完工有变化时记一次改期。"),
    "cancel": ("取消齐套排产计划", "modify", "取消选中的计划；取消后这张单可以重新排产。"),
}


def native_tool_description() -> str:
    """Return a concise description of the native Function collection."""
    operations = "；".join(f"{operation}（{spec['name']}）" for operation, spec in FUNCTION_CATALOG.items())
    return (
        f"供应链计划计算函数：{operations}。"
        "函数在运行时通过 sandbox_sdk.bkn 读取已绑定的知识网络；未传 business_date 时按 2027-02-25 计算。"
    )


def native_operation_description() -> str:
    return "可用具名函数：" + "、".join(FUNCTION_CATALOG)


__all__ = ["FUNCTION_CATALOG", "KIT_PLAN_ACTIONS", "KIT_SCHEDULE", "SCHEDULE_RULES", "native_operation_description", "native_tool_description"]
