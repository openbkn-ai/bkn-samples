"""Single source of truth for Agent-facing supply calculation Tool guidance."""

from __future__ import annotations

EXECUTION_USE_RULE = (
    '作为行动执行：先用 get_action_info 取参数定义，再用 execute_action 执行，最后用 get_action_execution 取结果。'
    '每个参数都要传：替代料、仓范围、需求日期、逾期在途等是业务假设，用户没说时按说明里的默认值显式传入，需求日期不设时传空字符串。'
    '检查执行结果里的 exit_code 和 result，执行状态 completed 不等于计算成功。'
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


KIT_SCHEDULE = {
    "name": "齐套排产",
    "operation": "kit_schedule",
    "description": "把一张需求预测单（整单）或其中一个产品排到一条产线的计划开工、完工时段，按计划开工日做齐套检查"
                   "（先保已签约欠货、不用成品、计入计划开工日前按期到货的在途），把结果写进齐套排产计划，不修改预测单。"
                   "同一预测单号 + 产品编码已有未取消的计划时修改这条计划（计划完工变了改期次数加一），否则新建；"
                   "计划状态传已取消时取消这条计划。返回计划号、齐套状态、齐套日和缺料。",
    "use_rule": "只通过三个齐套排产计划行动执行：建立（新建实例，object_input 传预测单号、产品编码〔整单传空字符串〕、产线编码、"
                "计划开工、计划完工、计划状态〔通常为已排〕、来源方案、排产人）、调整（修改实例，选中计划后传新的产线、计划开工、"
                "计划完工、来源方案、排产人）、取消（修改实例，选中计划后传排产人）。只查已排计划、齐套结论时用 Cypher 查齐套排产计划。",
}
RULE_USE = ("排程甘特的规则工具：输入 tasks（每条含 key、start、end、resource、values，values 里有 bill_no、product_code、"
            "line_code、planned_start、plan_status），一次最多 200 条；返回每条任务的 pass、severity（hard 或 soft）、text 和 related。"
            "问答里检查已排计划时，先用 Cypher 取齐套排产计划，再把计划转成 tasks 传入。")
SCHEDULE_RULES = {
    "kit_check_rule": {
        "name": "齐套检查",
        "description": "检查一批排产计划在计划开工时是否齐套：先保已签约欠货，再按开工先后在同一库存池上分配库存和按期到货的在途；"
                       "缺料时点名关键物料、缺口和预计到货，没下单的按采购提前期预估并提示尚未下采购申请。"
                       "开工早于最早可开工日为硬约束；related 是争同一物料的计划。已确认的计划已领料，视为齐套。",
        "use_rule": RULE_USE,
    },
    "line_check_rule": {
        "name": "产线可生产",
        "description": "检查一批排产计划的产线能否生产它的产品：产品的产品线要在产线的可生产产品线内，整单逐个产品判断；"
                       "排到工厂或不存在的产线也不通过。不通过为硬约束，并点名产线和产品线。",
        "use_rule": RULE_USE,
    },
}
KIT_PLAN_ACTIONS = {
    "create": ("建立齐套排产计划", "add",
               "排产：为一张预测单（整单）或其中一个产品新建齐套排产计划，按计划开工日记录齐套结论。"
               "同一预测单号 + 产品编码已有未取消的计划时改为修改这条计划，不会重复新建。"),
    "adjust": ("调整齐套排产计划", "modify",
               "改期或换线：对选中的计划改产线、计划开工、计划完工，重新做齐套检查；计划完工变了改期次数加一。"),
    "cancel": ("取消齐套排产计划", "modify", "把选中的计划状态改为已取消；已取消的计划不再有效，可以重新排产。"),
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
