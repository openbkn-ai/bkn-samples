# Manufacturing sample: metric, function, and Skill requirements

## Purpose and boundary

The sample supports a traceable manufacturing-fulfillment decision from a released plan snapshot through BOM-proven material issue, production, final quality, finished-goods receipt, and shipment. It uses 40 operational tables, 71 direct relations, and deterministic transaction evidence. It does not claim finite-capacity scheduling, dispatch optimization, lot genealogy, or root-cause workflows.

## Metrics

| ID | Metric | Definition | Grain |
|---|---|---|---|
| `material_issue_coverage` | Material coverage | `issued_quantity / required_quantity` | Work-order material requirement |
| `available_inventory` | Available inventory | `on_hand_quantity - allocated_quantity` at the balance `as_of_date` | Product and inventory location |
| `final_quality_conformance` | Final quality conformance | Final lot accepted and result inside the linked specification limits | Work order |
| `shipment_eligibility` | Shipment eligibility | A shipment is complete only when order, accepted finished-goods receipt, accepted final inspection, and quantities all agree | Shipment |

## Deterministic functions

### `evaluate_work_order_fulfillment`

**Input:** `production_order_id`.

**Processing:** trace the released plan line, frozen BOM version and component, material requirement and issue, execution and final inspection, finished-goods receipt, inventory snapshot, and shipment. Recompute the four metrics and return stable evidence IDs.

**Output:** `fulfilled`, `blocked`, `quality_rejected`, `pending`, or `unknown`, with the first unmet gate and its evidence.

### `evaluate_shipment_gate`

**Input:** `shipment_id`.

**Checks:** order/receipt/inspection agreement, quantity bounds, accepted quality and receipt for a completed shipment, and zero shipped quantity for blocked, rejected, or pending branches.

**Output:** `eligible: boolean`, delivery state, failure reason codes, and source record IDs.

## Skill

### `analyze_manufacturing_fulfillment`

Answer a business question about whether a plan or work order can be fulfilled. It calls the two functions, presents only model-proven findings in the requested language, and names missing evidence instead of inventing scheduling, purchasing, or maintenance recommendations.

## Acceptance

`WO-1001` is fulfilled: 122/122 material issued, accepted final inspection, 120 accepted finished goods, and 120 completed shipment. Material-shortage work orders have zero available raw inventory at the 2027-03-31 snapshot and cannot ship. Quality-rejected and pending branches also have zero shipped quantity. MFG-18 exercises these gates across all 50 shipments.
