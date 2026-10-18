"""Single source of truth for Agent-facing supply calculation Tool guidance."""

from __future__ import annotations


def _spec(
    name: str,
    operation: str,
    description: str,
    *,
    use_when: str = "按该函数的适用场景选择。",
    do_not_use_when: str = "问题不属于该业务场景时不要使用。",
    minimum_business_inputs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "operation": operation,
        "description": description,
        "use_when": use_when,
        "do_not_use_when": do_not_use_when,
        "minimum_business_inputs": minimum_business_inputs or [],
    }


FUNCTION_CATALOG = {
    "bom_list": _spec(
        "BOM清单",
        "bom_list",
        "适用场景：查看产品 BOM 结构、层级和单耗。输入：产品编码，可选层数和是否包含替代料。结果：默认返回结构统计和一级主料；明确要求明细时才分页返回。",
        use_when="需要了解一个产品的结构、一级主料或物料数量时使用。",
        do_not_use_when="需要反查某物料影响哪些产品，或判断多个产品的争用时不要使用。",
        minimum_business_inputs=["product"],
    ),
    "bom_shared_list": _spec(
        "产品BOM共用清单",
        "bom_shared_list",
        "适用场景：比较两款及以上产品的共同子料。输入：至少两个产品编码，可选层数和是否包含替代料。结果：共同子料结构，不含库存或争用判断。",
    ),
    "layered_inventory": _spec(
        "子料分层库存",
        "layered_inventory",
        "适用场景：查看产品 BOM 子料在指定仓范围的可用库存。输入：产品编码，可选层数和仓范围。结果：各层子料、可用量、占用展示和实际仓范围。",
    ),
    "substitute_status": _spec(
        "替代料状态",
        "substitute_status",
        "适用场景：确认产品或物料是否存在替代料及候选料库存。输入：产品编码或物料编码（二选一），可选仓范围和替代料策略。结果：替代组、候选料、可用量和策略状态。",
    ),
    "theoretical_build": _spec(
        "理论可产",
        "theoretical_build",
        "适用场景：判断现有库存按逐层净扣策略支持再制造多少成品。输入：产品编码、替代料策略，仓范围默认全仓，显式范围优先。结果：默认返回策略支持再制造量和瓶颈料；传 report_grain=full 才返回全部物料约束；不含成品库存和在途。",
    ),
    "total_sellable": _spec(
        "合计可售",
        "total_sellable",
        "适用场景：判断当前最多可销售多少成品。输入：产品编码、替代料策略，生产仓和成品仓默认全仓，可显式指定。结果：成品可用、理论可产和合计可售；不含在途。",
        use_when="客户询问现货或当前可售能力、成品现货是否覆盖需求时使用。",
        do_not_use_when="需要生产排程、采购到货日期或制造延期解释时不要用倒排替代。",
        minimum_business_inputs=["product", "substitute_enabled"],
    ),
    "kitting_net_demand": _spec(
        "要X套净需求与齐套",
        "kitting_net_demand",
        "适用场景：判断指定数量是否齐套并找出缺料。输入：产品编码、需求套数、替代料策略，默认全仓、不计PO；先扣成品及逐层组件库存。结果：默认返回齐套结论、全部缺料清单及每项按当前需求快照建议补货量；传 report_grain=full 才返回全部物料明细。",
    ),
    "shared_contention": _spec(
        "共用料与多需求争用",
        "shared_contention",
        "适用场景：判断多条需求同时承接时的共用物料争用。输入：至少两条产品与数量需求，数组顺序代表扣减优先级。结果：默认返回逐单满足状态和缺料清单；传 report_grain=full 才返回逐料分配和完整剩余池。",
        use_when="多个产品有明确数量，需要判断能否同时承接时使用。",
        do_not_use_when="只有一个产品，或数量缺失而只需比较结构时不要使用。",
        minimum_business_inputs=["demands", "substitute_enabled"],
    ),
    "max_build_without_po": _spec(
        "无需采购最大可产",
        "max_build_without_po",
        "适用场景：判断不新增采购时还能生产多少。输入：产品编码、替代料策略，仓范围默认全仓，显式范围优先。结果：默认返回策略支持再制造量和瓶颈料；传 report_grain=full 才返回全部物料约束；不含成品库存和在途。",
    ),
    "leadtime_days": _spec(
        "标准交期",
        "leadtime_days",
        "适用场景：查询单个物料的标准提前期。输入：物料编码。结果：leadtime_days、caliber（purchase/production）、material_attribute、source_field、unit 及正式物料 object_type_id。外购/委外取采购固定提前期，其他属性取生产固定提前期；缺失属性沿用生产默认并标记 attribute_missing，不代表已确认物料属性。",
    ),
    "supply_status": _spec(
        "供应状态诊断",
        "supply_status",
        "适用场景：在倒排中已有到位日和毛需求时诊断单料供应状态。输入：物料编码、到位日、毛需求、business_date，可选仓范围（默认全仓）。结果：on_time_covered、on_time_shortage_qty、按期库存/PO净未收数量及逐行日期证据；到货日晚于业务日且不晚于需要日的未关闭PO才计按期供给，过期和无日期PO不计已确认覆盖。",
    ),
    "open_forecast_count": _spec(
        "未关闭预测单数",
        "open_forecast_count",
        "适用场景：统计某产品或全部产品的未关闭预测单数量。输入：可选产品编码。结果：默认返回未关闭张数与排除口径；传 report_grain=full 才返回预测单 ID 列表，不代表预测需求数量。",
    ),
    "backward_plan": _spec(
        "生产计划齐套倒排",
        "backward_plan",
        "适用场景：核查已有预测单或新客户需求能否按截止日交付。输入：已有预测单时只需预测单号和替代料策略；新增需求提供产品、数量、截止日和替代料策略。结果：先给成品直发或生产计划模式，再给客户最早可用日期、客户延期天数、内部最大延迟、缺料和供应状态；Sample 默认业务日期为 2026-08-25。",
        use_when="成品现货不足，或需要生产排程、采购到货风险和延期解释时使用。",
        do_not_use_when="成品现货已覆盖客户数量、可直接发货时不要用制造倒排否定直发结论。",
        minimum_business_inputs=["product", "demand_qty", "demand_end", "substitute_enabled"],
    ),
    "material_where_used": _spec(
        "物料反查产品",
        "material_where_used",
        "适用场景：判断一个物料缺货、交期变化或替代变更会影响哪些产品。输入：物料编码。结果：affected_product_count 和产品清单；默认将替代料分支计入影响；传 report_grain=full 才返回命中 BOM 路径。",
        use_when="需要从物料反查受影响产品、识别通用料或分析缺料影响时使用。",
        do_not_use_when="只需查看某一个产品自身 BOM 结构时不要使用。",
        minimum_business_inputs=["material_code"],
    ),
}


def native_tool_description() -> str:
    """Return a concise description of the native Function collection."""
    operations = "；".join(
        f"{operation}（{spec['name']}）" for operation, spec in FUNCTION_CATALOG.items()
    )
    return (
        "供应链原生函数目录。按业务问题选择具名函数："
        f"{operations}。"
        "每个函数只接收本业务问题所需参数，并在运行时通过沙箱预装的 bkn_osdk 读取已绑定的知识网络；"
        "backward_plan 未传 business_date 时默认 2026-08-25。"
    )


def native_operation_description() -> str:
    return "可用具名函数：" + "、".join(FUNCTION_CATALOG)


__all__ = ["FUNCTION_CATALOG", "native_operation_description", "native_tool_description"]
