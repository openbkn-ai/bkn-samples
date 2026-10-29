# 输入输出契约：产品可售能力（S2）

使用已发布的 **合计可售** 函数。函数自行读取 BKN 中的 BOM 与库存，Skill 不重写可售公式。本契约描述字段和含义，不提供固定产品的结果样例。

## user_input

| 字段 | 类型与含义 |
|---|---|
| knowledge_network_id | 当前知识网络标识 |
| product_query | 用户给出的产品名称或编码，须解析成唯一编码 |
| substitute_enabled | 用户明确的布尔值；缺省时先确认 |
| production_scope / finished_goods_scope | 可选生产仓与成品仓范围 |

## 函数调用合同

调用 **合计可售** 时传入唯一产品编码、替代料策略，以及需要时的生产仓/成品仓范围。函数返回成品可用、理论可产、合计可售及实际仓范围。

Agent 只解释函数返回值：需要了解生产瓶颈时调用 **理论可产**，默认即可取得理论可产量、瓶颈和约束数量；只有需要逐料诊断时才传 `report_grain=full`。需要查看库存分布时调用 **子料分层库存**。Agent 不读取源码、不传快照或内部会话字段，也不在本地重算可售能力。禁止 CSV 或数据库直连作为运行时输入。

## analysis_result

| 字段 | 类型与含义 |
|---|---|
| product_code | 实际解析的产品编码 |
| fg_qty | 数值，成品仓可用数量 |
| theoretical_build_qty | 数值，现有物料支持的新增制造量 |
| total_sellable_qty | 数值，函数计算的成品与新增制造合计 |
| substitute_enabled | 实际采用的布尔策略 |
| finished_goods_filter / production_filter | 字符串数组，函数实际使用的仓范围 |
| include_in_transit | 布尔值，本能力不计在途 |

字段名必须与函数出参一致。不得由 Agent 猜测仓范围或填入文档样例数值。报告须声明：不是交期承诺；不得把 `total_sellable_qty` 表述为某日可交数量。
