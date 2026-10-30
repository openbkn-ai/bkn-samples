---
name: procurement-follow-up
description: >
  Use for purchasing-manager questions on knowledge network supply_ontology_en: open and
  overdue purchase order lines, deliveries due today or in a period, which suppliers and
  buyers to chase, which shortage materials have open orders and which need a new order,
  purchase lead times and earliest arrival, and tracing a purchase line back to its
  request, MRP plan and forecast.
---

# Purchase follow-up

Answer the purchasing manager's questions about open purchases, expediting, new orders and document trace. Use Cypher for open purchases, suppliers and lead times; call a function when you first need to know which materials are short.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2026-08-25; "now", "today" and "current" mean this date.
- Open purchase line = close status `rowclosestatus_title` and terminate status `rowterminatestatus_title` are both Open, and open quantity `qty - actqty > 0`.
- Lines with `deliverdate` before the business date are overdue: the supplier missed the date, so chase them, but they are not firm supply. Lines due on or after the business date count on their due date; a line due today is due today.
- "Due in a period" counts lines whose due date falls in the period, both ends included; "the next 30 days" runs from the day after the business date through day 30.
- Earliest arrival of a new order = business date + the material's standard purchasing lead time `purchase_fixedleadtime` in days.
- A supplier's responsible buyer is `purchaserid_name` on the supplier record.
- Shortages are the bottom-level gaps after netting the BOM level by level: finished goods first, then component stock at each level, expanding only the net shortage. A material with open purchases at least as large as its shortage can be expedited; with too little or nothing on order it needs a new order.

## When to call a function

- To know which materials a product's backlog, new order or work order is short of and by how much, call **Demand_Coverage_and_Shortages** (`demand_coverage`), then use Cypher for those materials' open purchases and lead times. Omit `reserve_signed_backlog` when evaluating the backlog itself; pass `true` for a new order that must protect backlog; pass `chase_overdue_po=true` when assuming overdue purchases are chased in.
- To know how many units a product can build, which material blocks it, or how many more chasing overdue purchases would allow, call **Buildable_Quantity_and_ATP** (`build_capacity`) with `products` as a list of product codes, all in one call.
- Use Cypher, not a function, for open purchases, overdue lines, suppliers, buyers, lead times, arrival dates and document trace.

## Cypher patterns

Object types are prefixed `supply_ontology_en_`. Dates are `YYYY-MM-DD` strings and compare as text. Variable-length paths and `UNWIND` are not supported.

- Open and overdue lines: `MATCH (po:supply_ontology_en_po) WHERE po.rowclosestatus_title = 'Open' AND po.rowterminatestatus_title = 'Open' AND po.qty - po.actqty > 0 RETURN po.billno, po.supplier_name, po.supplier_number, po.material_number, po.qty - po.actqty AS open_qty, po.deliverdate`; add `AND po.deliverdate < '2026-08-25'` for overdue lines.
- By supplier: `RETURN po.supplier_name, count(*) AS lines, sum(po.qty - po.actqty) AS open_qty ORDER BY lines DESC`; count suppliers with `count(DISTINCT po.supplier_number)`.
- Suppliers a buyer handles: `MATCH (s:supply_ontology_en_supplier) WHERE s.purchaserid_name = '<name>' RETURN s.supplier_code`, then join purchase lines with `po.supplier_number IN [...]`.
- Open purchases for a set of materials: `WHERE po.material_number IN ['<material 1>', '<material 2>']`.
- Material lead time: `MATCH (m:supply_ontology_en_material) WHERE m.material_code = '<material>' RETURN m.purchase_fixedleadtime, m.materialattr`
- Document trace: `MATCH (po:supply_ontology_en_po {billno: '<purchase order>', material_number: '<material>'})-[:supply_ontology_en_pr2po]->(pr:supply_ontology_en_pr)-[:supply_ontology_en_pr2mrp]->(m:supply_ontology_en_mrp)-[:supply_ontology_en_mrp2fcst]->(f:supply_ontology_en_forecast) RETURN DISTINCT pr.billno, m.billno, f.billno, f.material_number`. A purchase line maps to its requisition line by source requisition line and material; one forecast can cover several products.
- Stock: `MATCH (i:supply_ontology_en_inventory) WHERE i.material_code = '<material>' AND i.stock_status = 'Available' RETURN sum(i.available_inventory_qty)`

## How to answer

Lead with the conclusion (whom to chase, what to order, earliest arrival), then the basis: purchase order numbers, suppliers, open quantities, due dates, overdue or not. List every item in list questions; never truncate. When the data has no answer or the rule is unclear, say so; never guess. Every conclusion is follow-up advice and does not place orders or contact suppliers.
