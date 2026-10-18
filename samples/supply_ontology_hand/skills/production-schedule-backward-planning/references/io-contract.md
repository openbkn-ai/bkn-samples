# 输入输出契约：生产计划倒排（S1）

## user_input

```json
{
  "knowledge_network_id": "supply_ontology_hand",
  "product_query": "382-000005",
  "forecast_id": "FC-001",
  "demand_end": "2026-05-14",
  "demand_qty": 50,
  "business_date": "2026-08-25",
  "warehouse_scope": "production_available",
  "substitute_enabled": false,
  "report_grain": "summary"
}
```

- `product_query`、`demand_end`、`demand_qty`、`substitute_enabled` 必填；`forecast_id` 可选；`business_date` 缺省时为 `2026-08-25`。
- 一个产品对应一张需求预测；名称命中多个产品编码时先追问。
- 无日期或替代策略未确认时，不下齐套或交期结论。

## 函数调用合同

使用已发布的 **生产计划齐套倒排** 函数。函数调用只传业务参数，函数在运行时自行读取知识网络中的预测、BOM、库存、采购和 MRP 事实。

已有预测单时，函数校验产品、数量和截止日与预测一致；新增客户需求可不传 `forecast_id`，直接以产品、数量、截止日倒排。Agent 不读取 Skill 源码、不传快照、Token 或内部会话字段，也不在本地重写倒排算法。

函数不可用时，可分别调用 **要 X 套净需求与齐套** 和 **标准交期** 解释已知风险；此时应明确“无法形成完整倒排结论”。

## analysis_result

```json
{
  "product_code": "382-000005",
  "forecast_id": "FC-001",
  "demand_end": "2026-05-14",
  "demand_qty": 50,
  "business_date": "2026-08-25",
  "warehouse_filter": "production_available",
  "finished_goods_qty": 534,
  "fulfillment_mode": "finished_goods",
  "production_plan_required": false,
  "customer_earliest_available_date": "2026-08-25",
  "customer_late_days": 0,
  "can_deliver_on_time": false,
  "max_delay_days": 12,
  "delay_a": [],
  "delay_b": [],
  "supply_status_summary": {},
  "gaps": []
}
```

- `business_date`、`warehouse_filter`、`finished_goods_qty`、`fulfillment_mode` 必须回显。
- `fulfillment_mode=finished_goods` 表示成品现货已覆盖需求：`can_deliver_on_time=true`、最早可用日为业务日期，**不进入制造倒排**。
- `fulfillment_mode=production_plan` 表示现货不足：`customer_earliest_available_date` / `customer_late_days` 用于客户交期沟通；`max_delay_days` 仅表示内部倒排风险，不能直接表述为客户延期天数。
- 报告同时说明数据范围、替代策略与所用计算口径。

后续处置只输出人工建议；本版本不创建监控、采购申请、采购订单或 ERP 记录。
