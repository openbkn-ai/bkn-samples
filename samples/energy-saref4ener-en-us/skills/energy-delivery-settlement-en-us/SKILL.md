---
name: energy-delivery-settlement-en-us
description: >
  Use for response duty officer and settlement clerk questions on knowledge network energy_saref4ener_en_us:
  execution receipts, meter readings and corrections, verified energy and delivery ratio, threshold, revenue
  and customer compensation, net, ledger differences, settlement snapshots, and settlement as known on an earlier day.
---

# Delivery and settlement

Answer duty and settlement questions about execution, metering and settlement. Use Cypher for receipts, readings, the ledger and settlement snapshots; call a function to work out verified energy, delivery ratio, revenue and compensation.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-28; March events cannot be settled yet and cancelled events are not settled.
- "As of a day" counts only records known by that day; readings and baselines take the latest version per meter (device), date and block; a duplicate with the same content counts once, and conflicting content is undeterminable.
- Only allocations with a completed receipt count as delivered; failed or declined count zero; a missing receipt is undeterminable. Measured reduction = approved baseline × hours − valid reading (not below zero), shared in proportion to committed energy when one device serves several events in a block. Delivery ratio = verified ÷ committed energy, empty when nothing was committed.
- Revenue = verified energy × reward rate only when the delivery ratio meets the minimum (equal counts); customer compensation = shared energy × offer cost, paid regardless; revenue and compensation are each rounded to the cent, and net may be negative.
- The ledger uses the latest posted row dated on or before the day; two conflicting postings on one date cannot be reconciled; no posting is empty, not zero.

## When to call a function

- `settlement_assessment`: an event's committed energy, verified energy, delivery ratio, revenue, compensation, net and ledger difference. Pass `event_ids`, `as_of_date`, `knowledge_date` (an earlier day, or a date before or after a correction, to see what was known then).
- Use Cypher for receipt counts, reading versions, ledger rows and settlement snapshots; settlement snapshots only record 2027-02-28, invalid ones cannot be used and valid ones still need checking against the function. `event_ids` takes up to 20 events per call across dates and blocks; for all past events pass 20 at a time in date order, about three calls, never one block per call. After a function returns, check `completeness` and `issues`.

## Cypher patterns

The OpenBKN 0.2.1 mainline supports WITH, CASE and aggregation, not variable-length paths or UNWIND. Code columns hold English codes.

- Receipts: `MATCH (x:execution_logs)-[:execution_to_allocation]->(a:dispatch_allocations) WHERE a.event_id = '<event>' RETURN x.allocation_id, x.status_code, x.reason, x.revision` (take the highest revision per allocation).
- Readings: `meter_readings` with `meter_id`, `response_date`, `block_code`, `actual_kwh`, `quality_code`, `revision`, `known_date`.
- Ledger: `MATCH (s:settlements) WHERE s.event_id = '<event>' RETURN s.settlement_id, s.posted_date, s.revenue_cny, s.cost_cny, s.status_code`
- Settlement snapshot: `MATCH (s:settlement_snapshots) WHERE s.event_id = '<event>' RETURN s.delivery_ratio, s.revenue_cny, s.quality_code`

## How to answer

Lead with the conclusion (how much was delivered, whether the threshold was met, revenue and compensation, whether it reconciles), then the basis: allocations, receipts, readings, ledger rows and dates. List every item in list questions. When something is undeterminable, name the blocking record, never zero. Every conclusion is advice and pays nothing.
