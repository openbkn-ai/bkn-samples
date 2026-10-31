---
name: manufacturing-order-supply-en-us
description: >
  Use for order fulfilment and purchasing/materials questions on knowledge network manufacturing_industry_en_us:
  units owed, late and split shipments, replacement work orders, forecast and plan coverage, work order material
  requirements, completeness and blocking, overdue, rejected and late purchases, improper issues, stock, and order-to-shipment traces.
---

# Orders and materials

Answer order fulfilment and purchasing/materials questions. This sample has no functions; query with Cypher and apply the rules below.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-28; November to February have happened and March work orders are the plan; inventory is the 2027-02-28 snapshot.
- The requested date is the sales order's `requested_delivery_date` (one date per order). Units owed = order line ordered quantity − shipped quantity. Once fully shipped, a line is late if its last shipment is after the requested date, days late = last shipment date − requested date; a line still short after its requested date is also late, and say what holds it up: scrap, rejected inspection, still in production, inspection pending, finished but not shipped, or missing material.
- An order line can have several work orders: when the original is rejected at inspection, a replacement work order remakes the same line.
- Material requirement = work order quantity × quantity per × (1 + scrap factor), rounded up; issued ≥ requirement is complete.
- A work order is blocked when its BOM revision is not frozen, or when its planned start (production plan line `planned_start_date`) has arrived and material is incomplete. One whose planned start has not arrived and has no material issued yet is not blocked.
- Material may be issued only from accepted receipts; issuing from a receipt pending inspection or rejected is improper.
- Purchases are measured against the expected receipt date: a later receipt is late; an order whose expected date is before the business date and whose accepted quantity is below the ordered quantity is overdue, and rejected receipts do not count.
- Available = on hand − allocated; stock in the inspection hold cannot be issued.
- Plans are summed from production plan lines by the month of the work order's due date and compared with that month's forecast; coverage = planned ÷ forecast, two decimals.

## Cypher patterns

Object type names are the labels; relation type names are "sourcetable_foreignkey_to_targettable". Dates are YYYY-MM-DD strings. The OpenBKN 0.2.1 mainline supports WITH, CASE and aggregation, not variable-length paths or UNWIND. Status values are English codes (completed, blocked, released, in_production, accepted, rejected, pending_inspection, issued, partial, awaiting_issue).

- Order lines and dates: `MATCH (l:sales_order_lines)-[:sales_order_lines_sales_order_id_to_sales_orders]->(o:sales_orders) RETURN l.sales_order_line_id, l.product_id, l.ordered_quantity, o.customer_id, o.requested_delivery_date`
- Shipped: `MATCH (s:shipments) RETURN s.sales_order_line_id, sum(s.shipped_quantity) AS shipped, max(s.shipment_date) AS last_date, count(*) AS shipments`
- Work orders of a line: `MATCH (w:production_orders) WHERE w.sales_order_line_id = '<line>' RETURN w.production_order_id, w.status, w.requested_quantity, w.due_date`
- Requirements: `MATCH (r:production_order_material_requirements)-[:production_order_material_requirements_bom_component_id_to_bom_components]->(b:bom_components) WHERE r.production_order_id = '<work order>' RETURN r.product_id, r.required_quantity, r.issued_quantity, r.status, b.quantity_per, b.scrap_factor`
- Blocking: compare `production_orders.bom_version_id` with `product_bom_versions.status`; take `planned_start_date` from `production_plan_lines` by `production_order_id`.
- Issue sources: `MATCH (i:material_issue_transactions)-[:material_issue_transactions_goods_receipt_id_to_goods_receipts]->(g:goods_receipts) RETURN i.material_issue_transaction_id, i.production_order_id, i.issued_quantity, g.goods_receipt_id, g.inspection_status`
- Purchases and receipts: `MATCH (l:purchase_order_lines)-[:purchase_order_lines_purchase_order_id_to_purchase_orders]->(p:purchase_orders) RETURN p.purchase_order_id, p.supplier_id, p.expected_receipt_date, l.purchase_order_line_id, l.product_id, l.ordered_quantity`; receipts are `goods_receipts` with `purchase_order_line_id`, `received_quantity`, `received_date`, `inspection_status`.
- Stock: `inventory_balances` with `on_hand_quantity`, `allocated_quantity`, `available_quantity` and `inventory_location_id` (LOC-SZ-QI is the inspection hold).
- Forecast and plan: `demand_forecasts` (`forecast_period` is YYYY-MM); `production_plan_lines.planned_quantity`, month from the work order's `due_date`.
- Trace: inspection lots `quality_inspection_lots`, finished goods receipts `finished_goods_receipts` and shipments `shipments` all carry `production_order_id`.

## How to answer

Lead with the conclusion (how many owed, how late, can it start, how much short, which purchase is the problem), then the basis: order lines, work orders, materials, purchases, receipts and dates. List every item in list questions. When the data does not hold the answer, say so; never guess. Every conclusion is advice and places, schedules or ships nothing.
