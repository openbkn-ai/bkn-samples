---
name: retail-inventory-fulfilment-zh-cn
description: >
  用于知识网络 retail_gs1_zh_cn 上仓配负责人和门店店长的问题：商品与地点、库存与在途、可用量及其原因、
  近效期和过期、订单配货与缺口、三月补货，以及按某天当时已知信息回看库存。
---

# 库存与履约

回答仓配和门店关于库存、订单和补货的问题。查主数据、读 2 月 28 日库存快照用 Cypher；问其他日期、库存为什么少、订单怎么配、要补多少时调用函数。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28，“现在、今天”指这一天。三月的预测和计划到货是计划，不算已有库存。
- “某天的情况”只算事件日期和记录日期都不晚于当天的实际事件。
- 数量按商品基准单位（件）计，按箱记录的乘以每箱件数。
- 可用 = 在库 − 隔离 − 召回封存 − 有效预留，最低为零；已过期批次可用为零；14 天内到期为近效期。质检不合格或没检完的批次全部隔离。
- 重复记录的事件只算一次，被冲正的不算；库存算不清的批次地点要说明原因，不能当成零。
- 订单按优先级、交期、订单号先后共用同一份库存，每行只用同地点、同商品、已检合格、按“今天和交期较晚者 + 最少剩余保质天数”仍未过期的批次，先到期先出；已逾期的未完成订单也要分配。
- 补货按三月预测日期先后，用可用库存和合格的计划到货逐次扣减，缺口就是建议补货量。

## 什么时候调用函数

- `inventory_asof`：其他日期或按更早某天已知信息的库存；要按批次说明为什么可用少（隔离、召回封存、预留、过期）；哪些库存算不清及原因。传 `product_ids`、`as_of_date`、`knowledge_date`（“当时已知”与业务日期相同；问后来补录的事件时传更晚的日期），可选 `location_ids`、`lot_ids`。
- `fulfillment_plan`：订单配货（`mode=orders`，可选 `order_ids`）或三月补货（`mode=replenishment`）。全公司统计传全部商品，最多 50 个。
- 今天的在库、在途、隔离、预留、可用合计直接读 `inventory_snapshots`；函数返回后检查 `completeness` 和 `issues`。

## Cypher 写法

对象类型名就是标签，日期是 YYYY-MM-DD 字符串。OpenBKN 0.2.1 主线支持 WITH、CASE 和聚合，不支持变长路径和 UNWIND。代码列（如 `event_type_code`、`result_code`、`status_code`、`location_type_code`）是英文代码，名称列是中文。

- 今天某商品某地点的库存：`MATCH (s:inventory_snapshots) WHERE s.product_id = '<商品>' AND s.location_id = '<地点>' RETURN sum(s.on_hand) AS on_hand, sum(s.in_transit) AS in_transit, sum(s.quarantined) AS quarantined, sum(s.reserved) AS reserved, sum(s.available) AS available`
- 过期或近效期：`MATCH (s:inventory_snapshots)-[:inventory_snapshots_by_lot_id]->(l:lots) WHERE s.location_id = '<地点>' AND s.on_hand > 0 RETURN l.lot_id, l.expiry_date, s.on_hand`，到期日早于今天为过期，14 天内为近效期。
- 未完成订单：`MATCH (o:orders) WHERE o.status_code = 'open' RETURN o.order_id, o.location_id, o.priority, o.due_date`；订单行在 `order_lines`（`quantity`、`min_shelf_days`）。
- 批次流向：`MATCH (m:movements)-[:movements_by_lot_id]->(l:lots) WHERE l.lot_id = '<批次>' RETURN m.event_type_code, m.source_location_id, m.destination_location_id, m.quantity, m.event_date ORDER BY m.event_date`
- 需求预测：`demand_forecasts` 的 `demand_date`、`quantity`；仓店类型在 `locations.location_type_code`（warehouse、store）。

## 回答方式

先给结论（多少、够不够、缺多少），再列依据：批次、地点、事件或订单、日期和数量。清单类问题列全。数据算不清时说明原因，不猜数。所有结论是建议，不代表已发货或已下单。
