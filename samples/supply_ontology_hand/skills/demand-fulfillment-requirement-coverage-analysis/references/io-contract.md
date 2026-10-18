# 输入输出契约：新需求覆盖（S3）

S3 使用已发布的 **产品 BOM 共用清单** 或 **共用料与多需求争用** 函数。函数自行读取 BKN 事实，Skill 不重写业务公式。

## user_input

```json
{
  "knowledge_network_id": "supply_ontology_hand",
  "demands": [
    {"product_query": "382-000005", "qty": 50, "priority": 1},
    {"product_query": "P61-000351", "qty": 60, "priority": 2}
  ],
  "substitute_enabled": false,
  "warehouse_scope": "production_available"
}
```

每个 `product_query` 必须先解析为唯一产品编码。数量只允许全部缺失或全部明确；部分缺失时先请用户补齐数量或确认改做纯结构分析。

## 函数调用合同

### 结构模式：数量全部缺失

调用 **产品 BOM 共用清单**，只输出共同子料及数量；不得输出满足、缺口或扣减结论。

### 争用模式：数量全部明确

调用 **共用料与多需求争用**。`demands` 数组顺序就是扣减顺序；函数仅把未关闭 PO 未清计入在途，PR 不进共享池。默认摘要可直接用于“能否同时承接”的业务答复；只有需要逐料分配或完整剩余池时才传 `report_grain=full`。

两个模式均由函数自行读取 BKN。Agent 不读取源码、不传快照或内部会话字段、不在本地重写争用计算。禁止 CSV 或数据库直连作为运行时输入。

## analysis_result：结构交

```json
{
  "knowledge_network_id": "supply_ontology_hand",
  "products": ["382-000005", "P61-000351"],
  "shared_count": 28,
  "caliber": "structure_intersect_only"
}
```

结构交只表示共同出现的 BOM 子件，不是争用，也不是满足结论。

## analysis_result：争用

```json
{
  "knowledge_network_id": "supply_ontology_hand",
  "demands": [
    {"product_code": "382-000005", "qty": 50},
    {"product_code": "P61-000351", "qty": 60}
  ],
  "substitute_enabled": false,
  "deduction_order": ["382-000005", "P61-000351"],
  "all_satisfied": false,
  "unsatisfied_demand_count": 0,
  "shared_shortage_count": 0,
  "warehouse_filter": [],
  "allocations": [],
  "report_grain": "summary"
}
```

`deduction_order` 必须使用函数返回值并原样回显。摘要中 `allocations[]` 给出逐单满足状态、`shortage_count` 和 `shortages`；不得用产品级可售替代物料级 `shortage`。仅在 `report_grain=full` 时，`allocations[].lines[]` 提供 `gross_requirement`、`allocated`、`shortage`、`shared`，并返回 `remaining`。结果只形成分析与调整建议，不自动创建采购申请或采购订单。
