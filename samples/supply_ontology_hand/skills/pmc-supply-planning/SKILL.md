---
name: pmc-supply-planning
description: >
  Use for PMC production-planning questions on knowledge network supply_ontology_hand:
  sales backlog and overdue orders, finished-goods stock, forecasts, BOM structure and
  where-used, how many sets can be built or promised, whether new orders or work orders
  are covered, and which materials block them.
---

# PMC 生产计划

回答计划经理关于欠货、接单、排产和备料的问题。查数、汇总、追关系用 Cypher；需要按 BOM 逐层净扣时调用函数。

## 默认口径

使用者没有另说时，按以下口径回答，并在结论里简短说明用了哪条口径。

- 业务日期 2026-08-25，“现在、今天、当前”都指这一天。
- 库存只算库存状态为“可用”的 `available_inventory_qty`，默认全公司所有仓；“不良”库存不能投产、不能发货。“成品仓”是苏州成品仓、乌鲁木齐成品仓、哈尔滨成品仓；“苏州工厂生产七仓”是苏州半成品仓、苏州成品仓、苏州电子原料仓、苏州无人机原料仓、苏州装配原料仓、乌鲁木齐成品仓、哈尔滨成品仓。
- 欠货 = 签约数量 − 已发货数量 > 0；承诺交期早于业务日期即逾期。补发顺序按承诺交期，再按订单号。
- 在途 = 采购订单行关闭状态和终止状态都是“正常”，且订购数量 − 实收数量 > 0。交期不早于业务日期的按交期计入；交期早于业务日期的是逾期在途，不算确定供给，只在使用者说“假设能催回来”时计入。
- “现在、用现有库存能做多少”只看库存；问某个日期前投料或交货时，再加该日期前（含当天）按交期到货的在途。
- 生产可做数量按 BOM 逐层净扣：先用成品，再每层先扣组件库存、只展开净缺；多张需求共用一个库存池。默认不用替代料，使用者允许时才用。
- 可承诺量 = 成品库存 + 现有库存还能生产的数量 − 该产品已签约欠货。接新单、谈预测都要先保已签约欠货。
- 未关闭预测 = 关闭状态不是“已关闭”。一张预测单可以有多个产品。现有库存能支撑多少预测按可承诺量算，不能只看成品库存。

## 什么时候调用函数

- **产品可做数量与可承诺量**（`build_capacity`）：某产品现在最多还能做多少、可承诺多少、还能接多少新单、被哪颗料卡住；允许替代料、只用某几个仓、某日前在途到货、逾期在途催回后能多做多少。
- **需求齐套与缺料**（`demand_coverage`）：一张或几张需求够不够、缺哪些料、各缺多少。
  - 评估欠单本身：不传 `reserve_signed_backlog`。
  - 评估新单且要先保欠货：`reserve_signed_backlog=true`。
  - 排生产工单、不动成品：`use_finished_goods=false`。
  - 多单同时来：按使用者给的先后放进 `demands`。
- 其他问题（欠货、库存、预测、工单、BOM 清单、反查用途、通用料）用 Cypher，不要调用函数。函数的 `limiting_materials` 和 `shortages` 是最底层缺料；要回答这些料有没有在途、交期多久，再用 Cypher 查采购订单和物料。

## Cypher 写法

对象类型带前缀 `supply_ontology_hand_`，例如 `supply_ontology_hand_salesorder`。日期是 `YYYY-MM-DD` 字符串，直接比较大小。平台不支持变长路径和 `UNWIND`。

- 欠货：`MATCH (s:supply_ontology_hand_salesorder) WHERE s.signing_quantity > s.shipping_quantity RETURN s.sales_order_id, s.customer_name, s.product_code, s.signing_quantity - s.shipping_quantity AS owed, s.promised_delivery_date`
- 成品或物料库存：`MATCH (i:supply_ontology_hand_inventory) WHERE i.material_code = '<编码>' AND i.stock_status = '可用' RETURN sum(i.available_inventory_qty)`；限定仓库时加 `AND i.warehouse IN [...]`。
- 整棵 BOM：从产品一次取全，`bom_level` 为 0 是产品自身，主料行 `alt_priority = 0`。`MATCH (p:supply_ontology_hand_product {material_number: '<产品>'})-[:supply_ontology_hand_prod2bom]->(b:supply_ontology_hand_bom) WHERE b.bom_level > 0 AND b.alt_priority = 0 RETURN DISTINCT b.material_code`；一级物料加 `b.bom_level = 1`。
- 反查用途：`MATCH (b:supply_ontology_hand_bom) WHERE b.material_code = '<物料>' AND b.alt_priority = 0 AND b.bom_level > 0 RETURN DISTINCT b.bom_material_code`
- 两个产品的通用料：分别 `collect(DISTINCT b.material_code)` 成列表 `a`、`b`，`RETURN size([x IN a WHERE x IN b])`。
- 未关闭预测：`supply_ontology_hand_forecast`，`closestatus_title <> '已关闭'`，数量 `qty`，产品 `material_number`。
- 生产工单：`supply_ontology_hand_mps`，任务状态 `taskstatus_title`（完工、开工、部分完工、未开工），未入库 = `qty - xkquainwaqty`。
- MRP 计划订单：`supply_ontology_hand_mrp`，`dropstatus_title = '未投放'`。
- 产品线和上架状态在物料对象：`supply_ontology_hand_material` 的 `huid_productline_name`、`product_status`。

## 回答方式

先给结论（能不能、多少、差多少），再列依据：用到的口径、订单或物料清单、关键数量。清单类问题列全，不截断。数据里查不到或口径不明确时直接说明，不猜数。所有结论是计划建议，不代表已经下单、发货或排产。
