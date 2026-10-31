---
name: manufacturing-production-quality-en-us
description: >
  Use for production lead and quality manager questions on knowledge network manufacturing_industry_en_us:
  BOMs, routings, machine capabilities and operator qualifications, work order progress, completed quantity, scrap
  and yield, execution compliance (capability, service day, qualification, shift), rejected lots, out-of-limit results,
  quality escapes and specification revisions, overdue maintenance and machines under repair.
---

# Production and quality

Answer production lead and quality manager questions. This sample has no functions; query with Cypher and judge by the rules below.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-28; November to February have happened and March work orders are the plan.
- Execution compliance: every execution must meet all four conditions; failing any one makes it non-compliant, and say which:
  1. the machine's capability status for the step's `required_capability_id` is qualified;
  2. the machine has no maintenance work order on the execution's start date (`started_date`);
  3. the operator's qualification for that capability is qualified with `valid_to` on or after the start date;
  4. the operator is assigned, in the weekly shift covering the start date, to the operation's work centre.
- Work order completed quantity = good quantity of the last operation; operation yield = good ÷ (good + scrap); work order yield = completed quantity ÷ work order quantity.
- Quality release: the lot is accepted and every measured value lies within the referenced specification's (`quality_specification_id`) limits, inclusive. A result recorded as pass with a value out of limits counts as a failure and is a quality escape; say whether that lot shipped. A product's current specification is the one whose status is active; older revisions are superseded.
- Maintenance: a maintenance work order planned before the business date and not completed is overdue; a machine under repair cannot be scheduled; a machine whose capability is suspended cannot do that work.
- Operators who can run a capability now: qualified, valid on or after the business date, and employed.

## Cypher patterns

Object type names are the labels; relation type names are "sourcetable_foreignkey_to_targettable". Dates are YYYY-MM-DD strings. The OpenBKN 0.2.1 mainline supports WITH, CASE and aggregation, not variable-length paths or UNWIND. Status values are English codes (qualified, suspended, in_training, active, left, assigned, planned, in_progress, completed, accepted, rejected, pending, pass, fail, superseded, available, under_repair).

- Execution to work order: `MATCH (e:production_execution_records)-[:production_execution_records_process_step_id_to_process_steps]->(s:process_steps)-[:process_steps_operation_id_to_manufacturing_operations]->(o:manufacturing_operations) RETURN e.execution_record_id, e.machine_id, e.operator_id, e.started_date, e.good_quantity, e.scrap_quantity, e.status, s.required_capability_id, o.work_center_id, o.production_order_id, o.sequence_number`
- Machine capability: `machine_capability_assignments` with `machine_id`, `capability_id`, `qualification_status`; machine status in `production_machines.status`.
- Qualifications: `operator_qualifications` with `operator_id`, `capability_id`, `qualification_status`, `valid_to`; employment in `operators.employment_status`.
- Shifts: `MATCH (a:operator_shift_assignments)-[:operator_shift_assignments_shift_id_to_shifts]->(t:shifts) RETURN a.operator_id, a.work_center_id, t.starts_date, t.ends_date` (each shift is one week).
- Maintenance: `maintenance_work_orders` with `machine_id`, `planned_date`, `status`.
- Inspection: `MATCH (r:quality_inspection_results)-[:quality_inspection_results_inspection_lot_id_to_quality_inspection_lots]->(l:quality_inspection_lots) RETURN l.inspection_lot_id, l.production_order_id, l.status, l.lot_quantity, r.characteristic_name, r.measured_value, r.lower_limit, r.upper_limit, r.result_status, r.quality_specification_id`
- Specifications: `quality_specifications` with `product_id`, `characteristic_name`, `lower_limit`, `upper_limit`, `effective_date`, `status`.
- BOM and routing: `product_bom_versions` (frozen is current), `bom_components`; `routings` and `routing_operations` (`sequence_number`, `work_center_id`, `required_capability_id`).
- Shipped or not: sum `shipments.shipped_quantity` by `production_order_id`; the customer is reached through `sales_order_line_id` → `sales_order_lines` → `sales_orders.customer_id`.

## How to answer

Lead with the conclusion (compliant or not, yield, releasable or not, what is overdue), then the basis: executions, machines, operators, shifts, results, specifications and dates. List every item in list questions and give the reason for each non-compliance. Every conclusion is advice and releases, dispatches or stops nothing.
