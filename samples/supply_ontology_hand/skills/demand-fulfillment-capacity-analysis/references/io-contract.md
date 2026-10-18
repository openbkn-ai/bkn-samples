# 输入输出契约：产品可售能力（S2）

使用已发布的 **合计可售** 函数。函数自行读取 BKN 中的 BOM 与库存，Skill 不重写可售公式。

## user_input

```json
{
  "knowledge_network_id": "supply_ontology_hand",
  "product_query": "382-000005",
  "substitute_enabled": false
}
```

`substitute_enabled` 缺省时必须先问。

## 函数调用合同

调用 **合计可售** 时传入唯一产品编码、替代料策略，以及需要时的生产仓/成品仓范围。函数返回成品可用、理论可产、合计可售及实际仓范围。

Agent 只解释函数返回值：需要了解生产瓶颈时调用 **理论可产**，默认即可取得理论可产量、瓶颈和约束数量；只有需要逐料诊断时才传 `report_grain=full`。需要查看库存分布时调用 **子料分层库存**。Agent 不读取源码、不传快照或内部会话字段，也不在本地重算可售能力。禁止 CSV 或数据库直连作为运行时输入。

## analysis_result

```json
{
  "knowledge_network_id": "supply_ontology_hand",
  "product_code": "382-000005",
  "fg_qty": 534,
  "theoretical_build_qty": 0,
  "total_sellable_qty": 534,
  "substitute_enabled": false,
  "finished_goods_filter": ["苏州成品仓", "乌鲁木齐成品仓", "哈尔滨成品仓"],
  "production_filter": [
    "苏州半成品仓",
    "苏州成品仓",
    "苏州电子原料仓",
    "苏州无人机原料仓",
    "苏州装配原料仓",
    "乌鲁木齐成品仓",
    "哈尔滨成品仓"
  ],
  "include_in_transit": false
}
```

字段名必须与函数出参一致。仓范围使用函数实际返回的 `finished_goods_filter`、`production_filter`，不得由 Agent 猜测。报告须声明：不是交期承诺；不得把 `total_sellable_qty` 表述为某日可交数量。
