---
name: procurement-follow-up
description: >
  Use for purchasing-manager questions on knowledge network supply_ontology_hand: open and
  overdue purchase order lines, deliveries due today or in a period, which suppliers and
  buyers to chase, which shortage materials have open orders and which need a new order,
  purchase lead times and earliest arrival, and tracing a purchase line back to its
  request, MRP plan and forecast.
---

# 采购跟进

回答采购经理关于在途、催货、新下单和单据追溯的问题。查在途、供应商、交期用 Cypher；要先算出缺哪些料时调用函数。

## 默认口径

使用者没有另说时，按以下口径回答，并在结论里简短说明用了哪条口径。

- 业务日期 2026-08-25，“现在、今天、当前”都指这一天。
- 在途采购行 = 关闭状态 `rowclosestatus_title` 和终止状态 `rowterminatestatus_title` 都是“正常”，且未到数量 `qty - actqty > 0`。
- 交期 `deliverdate` 早于业务日期的是逾期在途：交期已经失信，要催，但不算确定能到。交期不早于业务日期的按交期计入，交期等于今天算今天应到。
- “某段时间内应到货”按交期落在该区间统计，含两端；“接下来 30 天”从业务日期次日算到第 30 天。
- 新下单最早到货日 = 业务日期 + 物料标准采购提前期 `purchase_fixedleadtime` 天。
- 供应商的负责采购员看供应商档案的 `purchaserid_name`。
- 缺料是按 BOM 逐层净扣后的最底层缺口：先用成品，每层先扣组件库存，只展开净缺。有在途且未到数量不少于缺量的料可以催，在途不够或没有在途的要新下单。

## 什么时候调用函数

- 要知道某产品欠单、新单或工单缺哪些料、缺多少时，调用 **需求齐套与缺料**（`demand_coverage`），再用 Cypher 查这些料的在途和提前期。评估欠单本身不传 `reserve_signed_backlog`；评估新单且先保欠货传 `true`；假设逾期在途催回来时传 `chase_overdue_po=true`。
- 要知道某产品最多能做多少、卡在哪颗料、催回逾期在途后能多做多少时，调用 **产品可做数量与可承诺量**（`build_capacity`）。
- 只问在途、逾期、供应商、采购员、提前期、到货日、单据追溯时用 Cypher，不要调用函数。

## Cypher 写法

对象类型带前缀 `supply_ontology_hand_`。日期是 `YYYY-MM-DD` 字符串，直接比较大小。平台不支持变长路径和 `UNWIND`。

- 在途与逾期：`MATCH (po:supply_ontology_hand_po) WHERE po.rowclosestatus_title = '正常' AND po.rowterminatestatus_title = '正常' AND po.qty - po.actqty > 0 RETURN po.billno, po.supplier_name, po.supplier_number, po.material_number, po.qty - po.actqty AS open_qty, po.deliverdate`；逾期加 `AND po.deliverdate < '2026-08-25'`。
- 按供应商统计：`RETURN po.supplier_name, count(*) AS lines, sum(po.qty - po.actqty) AS open_qty ORDER BY lines DESC`；家数用 `count(DISTINCT po.supplier_number)`。
- 某采购员负责的供应商：`MATCH (s:supply_ontology_hand_supplier) WHERE s.purchaserid_name = '<姓名>' RETURN s.supplier_code`；再用 `po.supplier_number IN [...]` 关联采购行。
- 一组物料的在途：`WHERE po.material_number IN ['<物料1>', '<物料2>']`。
- 物料提前期：`MATCH (m:supply_ontology_hand_material) WHERE m.material_code = '<物料>' RETURN m.purchase_fixedleadtime, m.materialattr`
- 单据追溯：`MATCH (po:supply_ontology_hand_po {billno: '<采购订单>', material_number: '<物料>'})-[:supply_ontology_hand_pr2po]->(pr:supply_ontology_hand_pr)-[:supply_ontology_hand_pr2mrp]->(m:supply_ontology_hand_mrp)-[:supply_ontology_hand_mrp2fcst]->(f:supply_ontology_hand_forecast) RETURN DISTINCT pr.billno, m.billno, f.billno, f.material_number`。采购订单行按来源请购行和物料对应请购行；一张预测单可以有多个产品。
- 库存：`MATCH (i:supply_ontology_hand_inventory) WHERE i.material_code = '<物料>' AND i.stock_status = '可用' RETURN sum(i.available_inventory_qty)`

## 回答方式

先给结论（该催谁、该下什么单、最早哪天到），再列依据：采购订单号、供应商、未到数量、交期、是否逾期。清单类问题列全，不截断。数据里查不到或口径不明确时直接说明，不猜数。所有结论是跟进建议，不代表已经下单或联系供应商。
