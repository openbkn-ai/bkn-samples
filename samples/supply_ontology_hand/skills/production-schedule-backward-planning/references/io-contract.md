# 输入输出契约：生产计划倒排（S1）

使用已发布的 **生产计划齐套倒排**（backward_plan）。本契约仅解释字段，不预填固定产品的库存、节点数或日期结论。

## user_input

| 字段 | 类型与含义 |
|---|---|
| forecast_id | 可选字符串，精确保留前导零；一张预测的业务标识 |
| product_query | 用户给出的产品名称或编码，需解析为唯一编码 |
| demand_end / demand_qty | 新需求的截止日和数量 |
| business_date | 可选业务日，默认 2026-08-25 |
| warehouse_scope | 可选仓范围 |
| substitute_enabled | 必须明确的布尔策略 |
| report_grain | summary（默认摘要）或 full_tree（完整结果树） |

已有预测单时，可仅传 `forecast_id` 与替代料策略，由函数读取产品、数量和截止日；额外给出的业务字段必须与预测一致。新增客户需求则传产品、数量、截止日和替代策略。名称命中多个产品时先追问；缺日期或替代策略时不下确定结论。

## 函数调用合同

函数只接收业务参数，自行读取知识网络中的预测、BOM、库存、采购和 MRP。Agent 不读取 Skill 源码、不传快照、Token 或内部会话字段，也不在本地重写倒排算法。

函数不可用时，可用 **要 X 套净需求与齐套**、**标准交期** 解释已知风险，但必须明确无法形成完整倒排结论。

## analysis_result

| 字段 | 类型与含义 |
|---|---|
| product_code / forecast_id | 本次实际使用的产品和预测标识 |
| business_date / demand_end / demand_qty | 本次业务日、截止日、数量 |
| warehouse_filter / finished_goods_filter | 实际仓范围 |
| finished_goods_qty / root_net_demand | 成品可用数量及抵扣后的制造需求 |
| fulfillment_mode / production_plan_required | 成品覆盖或需要制造的模式 |
| customer_earliest_available_date | 标准模型最早可用日；未确认供应时可为空 |
| customer_earliest_lower_bound | 已知最早可用下限，不是承诺日期 |
| customer_late_days | 客户口径延期天数，未知时不补猜 |
| can_deliver_on_time | 标准模型判断，可为 true、false 或 null |
| nodes / node_count_total | 实际倒排节点与总数；完整树使用 full_tree |
| start_date / end_date | 满足目标交期所需的倒排计划，不是从今天采购的实际到货预测 |
| max_delay_days / delay_a / delay_b | 内部倒排风险，不能直接等同客户延期天数 |
| gaps / uncertain_supply_items | 未覆盖叶子料及待确认的供应事项 |

`fulfillment_mode=finished_goods` 只表示成品数量覆盖、不进入制造倒排；业务日期不晚于交付截止日时，标准日期模型才可支持按期，否则仍可能已迟交。不得把该模式恒等于 `can_deliver_on_time=true`。

报告回显业务日、仓范围、成品数量、模式、替代策略及采用口径。即使数量覆盖或模型返回 true，实际交付仍须确认分配、产能、质检和发运条件。

后续处置只输出人工建议；本版本不创建监控、采购申请、采购订单或 ERP 记录。
