---
name: manufacturing-order-supply-zh-cn
description: >
  用于知识网络 manufacturing_industry_zh_cn 上订单交付经理和采购与物料经理的问题：销售订单欠交、延误、分批发运和补做工单，
  需求预测与生产计划覆盖，工单物料需求、齐套与阻塞，采购逾期、拒收、延迟到货和违规发料，库存在手与可用，订单到发运的端到端追溯。
---

# 订单交付与物料采购

回答订单交付和采购物料人员的问题。本样例没有函数，全部用 Cypher 查询后按下面的口径计算。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28；十一月至二月已发生，三月工单是计划；库存是 2027-02-28 的快照。
- 要求交期取销售订单 `requested_delivery_date`（整单一个日期）。欠交 = 订单行订购数量 − 已发运数量。全部发完后最后一次发运晚于要求交期为延误，延误天数 = 最后发运日 − 要求交期；交期已过仍未发完也算延误，并说明卡在哪：报废少做、检验被拒、在制、检验未出结论、做完未发或缺料。
- 一个订单行可能有多张工单：原工单检验被拒，补做工单为同一订单行重做。
- 物料需求 = 工单数量 × 单耗 × (1 + 损耗率)，向上取整；已发不低于需求为齐套。
- 工单阻塞：BOM 版本不是已冻结，或计划开工日（生产计划行 `planned_start_date`）已到而物料不齐套。计划开工日未到、还没发料的不算阻塞。
- 只能从已接受的来料发料；从待检或已拒收来料发料是违规发料。
- 采购按预计到货日考核：到货晚于预计为延迟；预计日早于业务日期、已接受数量不足订购数量为逾期未到，拒收不算到货。
- 可用 = 在手 − 已分配；待检区库存不能发料。
- 计划按工单交期所在月汇总生产计划行，与当月预测比较；覆盖率 = 计划 ÷ 预测，保留两位小数。

## Cypher 写法

对象类型名就是标签，关系类型名是“源表_外键_to_目标表”。日期是 YYYY-MM-DD 字符串。OpenBKN 0.2.1 主线支持 WITH、CASE 和聚合，不支持变长路径和 UNWIND。状态取值是中文（已完成、已阻塞、已下达、生产中、已接受、已拒收、待检、已发料、部分发料、待发料）。

- 订单行与交期：`MATCH (l:sales_order_lines)-[:sales_order_lines_sales_order_id_to_sales_orders]->(o:sales_orders) RETURN l.sales_order_line_id, l.product_id, l.ordered_quantity, o.customer_id, o.requested_delivery_date`
- 已发运：`MATCH (s:shipments) RETURN s.sales_order_line_id, sum(s.shipped_quantity) AS shipped, max(s.shipment_date) AS last_date, count(*) AS shipments`
- 订单行的工单：`MATCH (w:production_orders) WHERE w.sales_order_line_id = '<订单行>' RETURN w.production_order_id, w.status, w.requested_quantity, w.due_date`
- 物料需求：`MATCH (r:production_order_material_requirements)-[:production_order_material_requirements_bom_component_id_to_bom_components]->(b:bom_components) WHERE r.production_order_id = '<工单>' RETURN r.product_id, r.required_quantity, r.issued_quantity, r.status, b.quantity_per, b.scrap_factor`
- 阻塞判断：`production_orders` 的 `bom_version_id` 对 `product_bom_versions.status`；`production_plan_lines` 按 `production_order_id` 取 `planned_start_date`。
- 发料来源：`MATCH (i:material_issue_transactions)-[:material_issue_transactions_goods_receipt_id_to_goods_receipts]->(g:goods_receipts) RETURN i.material_issue_transaction_id, i.production_order_id, i.issued_quantity, g.goods_receipt_id, g.inspection_status`
- 采购与来料：`MATCH (l:purchase_order_lines)-[:purchase_order_lines_purchase_order_id_to_purchase_orders]->(p:purchase_orders) RETURN p.purchase_order_id, p.supplier_id, p.expected_receipt_date, l.purchase_order_line_id, l.product_id, l.ordered_quantity`；到货看 `goods_receipts` 的 `purchase_order_line_id`、`received_quantity`、`received_date`、`inspection_status`。
- 库存：`inventory_balances` 的 `on_hand_quantity`、`allocated_quantity`、`available_quantity`，库位 `inventory_location_id`（LOC-SZ-QI 是待检区）。
- 预测与计划：`demand_forecasts`（`forecast_period` 为 YYYY-MM）；`production_plan_lines` 的 `planned_quantity`，月份按对应工单的 `due_date`。
- 追溯：检验批 `quality_inspection_lots`、成品入库 `finished_goods_receipts`、发运 `shipments` 都带 `production_order_id`。

## 回答方式

先给结论（欠多少、晚几天、能不能开工、缺多少、哪张采购有问题），再列依据：订单行、工单、物料、采购、来料和日期。清单类问题列全。数据里查不到时直接说明，不猜数。所有结论是建议，不代表已下单、排产或发货。
