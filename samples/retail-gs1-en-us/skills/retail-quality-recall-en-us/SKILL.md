---
name: retail-quality-recall-en-us
description: >
  Use for quality-lead questions on knowledge network retail_gs1_en_us: failed and pending
  inspections, quarantine, the lots and locations a recall reaches, units sold and not returned,
  affected orders, recall coverage, closed recalls, and data-trust issues such as duplicate,
  reversed or late-recorded events.
---

# Quality and recall

Answer quality-lead questions about inspection, quarantine, recalls and data trust. Use Cypher for inspection results, lot splits and recall snapshots; call a function to trace a recall from its root lot, to work out control by location, or to look back at what was known on a day.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-28; "as of a day" counts only actual events whose event date and recorded date are on or before that day.
- A lot whose latest inspection failed or is pending is fully quarantined; returns and active holds are quarantined too, never deducting the same units twice.
- An open recall reaches every downstream lot of its root lot through splits and transformations; their on-hand stock not already quarantined is recall-blocked. A closed recall blocks nothing and gets no recall assessment.
- Recall control by product and location: controllable = on hand + in transit of affected lots; controlled = the quarantined part; coverage = controlled ÷ controllable. When controllable is zero or stock cannot be determined, coverage cannot be calculated, which is not zero. Units sold are net of returns and listed separately.
- Affected orders: orders that shipped affected lots, and open orders holding a reservation on an affected lot.
- An event recorded twice counts once and a reversed event does not count; conflicting event copies, arrivals without dispatch, negative stock and returns exceeding sales make the related stock undeterminable.

## When to call a function

- `recall_assessment`: a recall's on hand, in transit, sold, returned, controlled, controllable, coverage, uncontrolled quantity and affected orders by product and location. Pass `recall_id`, `as_of_date`, `knowledge_date`.
- `inventory_asof`: stock of problem lots by location; stock as known on an earlier day; `trace_lot_id` to trace a lot's connected upstream and downstream lots; why stock cannot be determined (see `issues`).
- Today's recall control by product can be read from `recall_snapshots`. After a function returns, check `completeness` and `issues`.

## Cypher patterns

The OpenBKN 0.2.1 mainline supports WITH, CASE and aggregation, not variable-length paths or UNWIND, so follow `lot_links` one level at a time. Code columns hold English codes.

- Inspection results: `MATCH (i:inspections) WHERE i.result_code IN ['failed', 'pending'] RETURN i.lot_id, i.result_code, i.inspection_date` (take the latest inspection when a lot has several).
- Splits and transformations: `MATCH (k:lot_links)-[:lot_links_by_parent_lot_id]->(p:lots) WHERE p.lot_id = '<lot>' RETURN k.child_lot_id, k.child_quantity, k.link_type_code` (split or transform).
- Recalls: `recalls` with `root_lot_id`, `status_code` (open, closed), `announced_date`.
- Recall snapshot: `MATCH (r:recall_snapshots) WHERE r.recall_id = '<recall>' RETURN r.product_id, r.controlled_quantity, r.controllable_quantity, r.coverage_ratio`
- Duplicates or reversals: `movements` with `event_id`, `event_type_code`, `reversal_of`, `recorded_date`.

## How to answer

Lead with the conclusion (what is affected, how much is controlled, how much is left), then the basis: lots, locations, events, orders and dates. List every item in list questions. When stock is undeterminable or coverage unknown, say why and never treat it as zero. Every conclusion is advice and executes no recall or notice.
