---
name: retail-quality-recall-zh-cn
description: >
  用于知识网络 retail_gs1_zh_cn 上质量负责人的问题：质检不合格和待检批次、隔离、召回涉及的批次与地点、
  已售未退、受影响订单、召回控制比例、已关闭召回，以及重复、冲正、补录等数据可信问题。
---

# 质量与召回

回答质量负责人关于质检、隔离、召回和数据可信的问题。查质检结果、批次拆分、召回快照用 Cypher；要从根批次追召回、按地点算控制情况、或回看某天已知信息时调用函数。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28；“某天的情况”只算事件日期和记录日期都不晚于当天的实际事件。
- 最近一次质检不合格或还没检完的批次全部隔离；退货和有效的隔离单也要隔离，同一批货不重复扣。
- 进行中的召回从根批次沿批次拆分和转换找到所有下游批次；这些批次扣掉隔离后剩下的在库全部召回封存。已关闭的召回不再封存，也不做召回评估。
- 召回控制按商品和地点：可控制 = 受影响批次的在库 + 在途；已控制 = 其中已隔离的部分；控制比例 = 已控制 ÷ 可控制。可控制为零或库存算不清时比例算不出来，不是零。已售按销售减退回计，单独列出。
- 受影响订单：受影响批次已发货的订单，以及预留了受影响批次的未完成订单。
- 同一事件重复记录只算一次，被冲正的不算；事件内容冲突、到货找不到发货、负库存、退货多于销售都会让相关库存算不清。

## 什么时候调用函数

- `recall_assessment`：某个召回按商品和地点的在库、在途、已售、退回、已控制、可控制、控制比例、未控制量和受影响订单。传 `recall_id`、`as_of_date`、`knowledge_date`。
- `inventory_asof`：问题批次在各地点的库存；某天当时已知信息下的库存；`trace_lot_id` 追溯一个批次上下游相连的批次；库存算不清的原因（看 `issues`）。
- 今天召回按商品的已控制、可控制和控制比例直接读 `recall_snapshots`；函数返回后检查 `completeness` 和 `issues`。

## Cypher 写法

OpenBKN 0.2.1 主线支持 WITH、CASE 和聚合，不支持变长路径和 UNWIND，批次关系按 `lot_links` 一层一层查。代码列是英文代码，名称列是中文。

- 质检结果：`MATCH (i:inspections) WHERE i.result_code IN ['failed', 'pending'] RETURN i.lot_id, i.result_code, i.inspection_date`（一个批次有多次质检时取最近一次）。
- 拆分和转换：`MATCH (k:lot_links)-[:lot_links_by_parent_lot_id]->(p:lots) WHERE p.lot_id = '<批次>' RETURN k.child_lot_id, k.child_quantity, k.link_type_code`（split 为拆分，transform 为商品转换）。
- 召回：`recalls` 的 `root_lot_id`、`status_code`（open、closed）、`announced_date`。
- 召回快照：`MATCH (r:recall_snapshots) WHERE r.recall_id = '<召回>' RETURN r.product_id, r.controlled_quantity, r.controllable_quantity, r.coverage_ratio`
- 重复或冲正：`movements` 的 `event_id`、`event_type_code`、`reversal_of`、`recorded_date`。

## 回答方式

先给结论（涉及哪些、控制了多少、还差多少），再列依据：批次、地点、事件、订单和日期。清单类问题列全。算不清或比例未知时说明原因，不当成零。所有结论是建议，不代表已执行召回或通知。
