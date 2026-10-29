# 输入输出契约：新需求覆盖（S3）

S3 使用已发布的 **产品 BOM 共用清单** 或 **共用料与多需求争用** 函数。函数自行读取 BKN 事实，Skill 不重写业务公式。以下仅为字段契约，不提供固定产品的结果。

## user_input

| 字段 | 类型与含义 |
|---|---|
| knowledge_network_id | 当前知识网络标识 |
| demands | 需求数组；每项给产品名称或编码、需求数量及业务优先级 |
| substitute_enabled | 明确的布尔策略 |
| warehouse_scope | 可选仓范围 |
| demand_mode | 客户承接供货用 fulfillment；明确必须新增生产用 production |

每个 `product_query` 必须先解析为唯一产品编码，函数项使用 `product` 和 `qty`。数量只允许全部缺失或全部明确；部分缺失时先补齐，或确认改做纯结构分析。

## 函数调用合同

数量全部缺失时，调用 **产品 BOM 共用清单**，只输出共同子料及数量；不得输出满足、缺口或扣减结论。

数量全部明确时，调用 **共用料与多需求争用**。`demands` 数组顺序就是扣减顺序；未关闭 PO 的未清量计入在途，PR 不进共享池。客户供货先抵扣成品；必须新增生产则不抵扣。意图不明确时说明假设或澄清。默认摘要提供能否同时承接的结论；逐料分配或完整剩余池才使用 `report_grain=full`。

Agent 不读取源码、不传快照或内部会话字段、不在本地重写争用计算。禁止 CSV 或数据库直连作为运行时输入。

## analysis_result

| 模式及字段 | 类型与含义 |
|---|---|
| 结构：products / shared_count | 产品数组、共同子料数量，均读取实际返回值 |
| 结构：caliber | structure_intersect_only；结构共用不等于争用或满足 |
| 争用：deduction_order | 实际扣减顺序，按返回值回显 |
| 争用：all_satisfied | 所有需求是否均已覆盖 |
| 争用：unsatisfied_demand_count | 未满足需求条数，须与 allocations 一致 |
| 争用：shared_shortage_count | 共同物料的缺口项数，不能代替逐单是否满足 |
| 争用：warehouse_filter | 实际仓范围 |
| 争用：allocations | 逐单 satisfied、shortage_count、shortages |
| 完整结果：allocations[].lines / remaining | 逐料毛需求、分配、缺口、是否共用，以及剩余池 |

不得用产品级可售替代物料级 `shortage`。所有数量和布尔结果均来自本次函数调用。结果只形成分析与调整建议，不自动创建采购申请或采购订单。
