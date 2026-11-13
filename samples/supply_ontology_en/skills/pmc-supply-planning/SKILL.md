---
name: supply-en-pmc-supply-planning
description: >
  Use for PMC production-planning questions on knowledge network supply_ontology_en:
  sales backlog and overdue orders, finished-goods stock, forecasts, BOM structure and
  where-used, how many units can be built or promised, whether new orders or work orders
  are covered, which materials block them, and kit schedule plans (which demand is
  scheduled on which line, its kit result, rescheduling and cancelling).
---

# PMC production planning

Answer the planner's questions about backlog, order acceptance, scheduling and material preparation. Use Cypher for lookups, totals and following relations; call a calculation function when the BOM must be netted level by level.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-25; "now", "today" and "current" mean this date.
- Stock counts only `available_inventory_qty` with stock status Available, across every warehouse by default; Defective stock cannot be used in production or shipped. "Finished-goods warehouses" means Suzhou Finished Goods, Urumqi Finished Goods and Harbin Finished Goods; "the seven Suzhou plant production warehouses" means Suzhou Subassemblies, Suzhou Finished Goods, Suzhou Electronics, Suzhou Drone Materials, Suzhou Assembly, Urumqi Finished Goods and Harbin Finished Goods.
- Owed = signed quantity − shipped quantity > 0; owed orders with a promised date before the business date are overdue. Fill owed orders by promised date, then order number.
- Open purchase = purchase order line whose close status and terminate status are both Open, with ordered − received > 0. Lines due on or after the business date count on their due date; lines due earlier are overdue: they are not firm supply and count only when the user says to assume they are chased in.
- "Now" or "with current stock" means stock only; for issues or deliveries by a date, add open purchase lines due by that date (inclusive).
- Buildable quantity nets the BOM level by level: finished goods first, then at each level use component stock and expand only the net shortage; several demands share one stock pool. No alternates unless the user allows them.
- Available to promise = finished-goods stock + what current stock can still build − the product's signed backlog. New orders and forecasts must protect signed backlog first; give only the backlog-protected figure.
- "Finished-goods stock" and "stock on hand" mean the product's own Available stock across every warehouse; restrict to the three finished-goods warehouses only when the user says "finished-goods warehouses".
- "Stock on hand" is finished-goods stock only, not what can still be built: stock on hand still promisable = finished-goods stock − signed backlog − the quantity being shipped now.
- Open forecast = close status is not Closed. One forecast can cover several products, all delivered on the same day: the delivery date is `startdate` (Forecast Delivery Date) and `enddate` closes the demand window. An open forecast whose delivery date is before the business date is late. How much forecast current stock can support is the available to promise, not finished-goods stock alone.

## When to call a calculation function

The calculation functions are mounted on the network: call them directly with Context Loader `execute_tool`, copying `toolbox_id` (owner_id) and `tool_id` (capability_id) from discovery as they are. Substitutes (default false), warehouse scope (default all), need-by date and overdue purchases (default false) are business assumptions; when the user does not say, pass the default explicitly and state in the answer what the result assumes. Check `body.exit_code` and `result`: HTTP 200 alone does not mean the calculation succeeded.

- **Buildable_Quantity_and_ATP** (`build_capacity`): how many units a product can still build, how much it can promise, how much more it can accept, which material blocks it; with alternates, a warehouse scope, open purchases due by a date, or overdue purchases chased in. Pass `products` as a list of product codes; each is calculated on its own. When several products are needed, pass them in one call instead of calling once per product.
  - Which products' backlog neither stock on hand nor production can cover: first use Cypher to find products whose backlog exceeds finished-goods stock, then pass them all to this function in one call. A product is uncovered when `finished_goods_qty + buildable_qty < signed_backlog_qty`, and the gap is `signed_backlog_qty − finished_goods_qty − buildable_qty` (`available_to_promise` never goes below 0, so do not use it for this).
  - How many more units open purchases due by a date allow: run it again for the same products with `need_by` and subtract the two `buildable_qty` values.
- **Demand_Coverage_and_Shortages** (`demand_coverage`): whether one or more demands are covered, what is short and by how much.
  - Evaluating the backlog itself: omit `reserve_signed_backlog`.
  - New orders that must protect backlog: `reserve_signed_backlog=true`.
  - Planning a work order without touching finished goods: `use_finished_goods=false`.
  - Several orders at once: put them in `demands` in the order the user gives.
- Use Cypher, not a calculation function, for everything else (backlog, stock, forecasts, work orders, BOM lists, where-used, common parts). The functions' `limiting_materials` and `shortages` are bottom-level shortages; to say whether they have open purchases or how long they take, query purchase orders and materials with Cypher.

## Kit schedule plans

Scheduling results live in the kit schedule plan (`supply_ontology_en_kitplan`); the demand forecast itself is not changed. A plan covers a whole forecast bill (`product_code` empty) or one of its products on one production line; a forecast number + product code has at most one active plan (`plan_status` not Cancelled).

- Fields: `plan_id`, forecast number `bill_no`, `product_code`, line `line_code`, `planned_start`, `planned_finish`, `quantity` (empty for a whole bill), `kit_status` (Covered, Covered (Order Pending), Short), `kit_date`, `key_material`, `shortage_note`, `plan_status` (Scheduled, Confirmed, Cancelled; Confirmed means released to production), `reschedule_count`, `previous_finish`, `source_scenario`, `planner`, `planned_at`.
- The kit result is worked out when a plan is created or adjusted, for its planned start and together with the network's other active plans, the same as the schedule Gantt's kit check: signed backlog first, then confirmed and scheduled plans share stock and open purchases due by the start; a product already in production has drawn its materials and takes no more. Covered: everything is there at the start; the kit date is the start. Covered (Order Pending): the only missing materials have no purchase request yet and arrive before the start if ordered now; the plan can go ahead, but the requests must be placed soon; the shortage note lists them and the kit date is the earliest kitted date. Short: the gap cannot be closed by the start; the kit date is the earliest kitted date and a plan starting before it cannot be adopted. For "is it still covered now", run Kit_Check or Demand_Coverage_and_Shortages again instead of reading the stored result.
- Active plans: `MATCH (k:supply_ontology_en_kitplan) WHERE k.plan_status <> 'Cancelled' RETURN k.plan_id, k.bill_no, k.product_code, k.line_code, k.planned_start, k.planned_finish, k.kit_status, k.kit_date, k.key_material, k.plan_status`. Whether a forecast is scheduled: add `AND k.bill_no = '<forecast number>'`; no active plan means it still has to be scheduled.
- Lines are `supply_ontology_en_line`: plants are rows too (`line_kind` Plant, never scheduled); a line's `parent_code` is its plant, `max_parallel` is how many plans it can run at once and `product_lines` what it builds; a product's default line is its `line_code`. Stoppages are `supply_ontology_en_stoppage`; `resource_code` is a line or plant code, and a plant stoppage applies to all its lines.
- Run one of the three actions only when the user explicitly asks to schedule, reschedule or cancel (they change plan objects, so they are actions: `get_action_info` for the parameters, `execute_action` to run, `get_action_execution` for the result): Create Kit Schedule Plan (new instance; `object_input` carries `bill_no`, `product_code` [empty string for the whole bill], `line_code`, `planned_start`, `planned_finish`, `plan_status` [usually Scheduled], `source_scenario`, `planner`), Adjust Kit Schedule Plan (modify; `_instance_identities` holds the selected `plan_id`, then the new line, start, finish, scenario and planner) and Cancel Kit Schedule Plan (modify; the plan ID and planner). Say what will be written first; afterwards report the plan ID, kit status, kit date and key material from the result. Creating the same forecast (and product) again updates the existing plan instead of adding one.
- For "can these plans run as scheduled, which one will be short, can the line build it", call the Kit_Check and Line_Can_Build functions with `execute_tool` (the schedule Gantt uses the same rules): each item of `tasks` is `{key, start, resource, values}` with the plan ID as key, the planned start as start, the line code as resource, and `bill_no`, `product_code`, `line_code`, `planned_start`, `plan_status` in values. Kit_Check reserves signed backlog first, then allocates confirmed plans and then scheduled plans, each in start order, on one shared pool, so send all related plans in one call; a plan whose production has started (a started work order) has drawn its materials and passes. `at` is the earliest start and `related` lists the plans competing for the same material. To list what one plan is short of, call Kit_Check with `mode=detail`, one `task` and `query` (`group` one of late_po, overdue_po, no_pr, reserved; `keyOnly`, `search`, `offset`, `limit`) and list the returned table in full.

## Cypher patterns

Object types are prefixed `supply_ontology_en_`, e.g. `supply_ontology_en_salesorder`. Dates are `YYYY-MM-DD` strings and compare as text. Variable-length paths and `UNWIND` are not supported.

- Backlog: `MATCH (s:supply_ontology_en_salesorder) WHERE s.signing_quantity > s.shipping_quantity RETURN s.sales_order_id, s.customer_name, s.product_code, s.signing_quantity - s.shipping_quantity AS owed, s.promised_delivery_date`
- Product or material stock: `MATCH (i:supply_ontology_en_inventory) WHERE i.material_code = '<code>' AND i.stock_status = 'Available' RETURN sum(i.available_inventory_qty)`; add `AND i.warehouse IN [...]` for a warehouse scope.
- Whole BOM: one query from the product returns every level; `bom_level` 0 is the product itself and main parts have `alt_priority = 0`. `MATCH (p:supply_ontology_en_product {material_number: '<product>'})-[:supply_ontology_en_prod2bom]->(b:supply_ontology_en_bom) WHERE b.bom_level > 0 AND b.alt_priority = 0 RETURN DISTINCT b.material_code`; add `b.bom_level = 1` for first-level materials.
- Where-used: `MATCH (b:supply_ontology_en_bom) WHERE b.material_code = '<material>' AND b.alt_priority = 0 AND b.bom_level > 0 RETURN DISTINCT b.bom_material_code`
- Common parts of two products: `collect(DISTINCT b.material_code)` into lists `a` and `b`, then `RETURN size([x IN a WHERE x IN b])`.
- Open forecasts: `supply_ontology_en_forecast` with `closestatus_title <> 'Closed'`; quantity `qty`, product `material_number`.
- Work orders: `supply_ontology_en_mps`; task status `taskstatus_title` (Complete, Started, Partly Complete, Not Started); not yet received = `qty - xkquainwaqty`.
- MRP planned orders: `supply_ontology_en_mrp` with `dropstatus_title = 'Not Released'`.
- Product line and listing status are on the material: `supply_ontology_en_material` fields `huid_productline_name` and `product_status` (Listed, Unlisted).

## How to answer

Lead with the conclusion (yes or no, how many, how far short), then the basis: rules used, the orders or materials, key quantities. List every item in list questions; never truncate. When the data has no answer or the rule is unclear, say so; never guess. Every conclusion is planning advice and does not place or ship anything; only a kit schedule plan action schedules.
