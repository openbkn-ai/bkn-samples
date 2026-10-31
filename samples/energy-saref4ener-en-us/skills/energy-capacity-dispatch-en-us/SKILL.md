---
name: energy-capacity-dispatch-en-us
description: >
  Use for aggregator operations and site energy manager questions on knowledge network energy_saref4ener_en_us:
  customers, sites, devices and meters, March events and load forecasts, eligible capacity and exclusion reasons,
  site caps, events sharing a block, and the priority- and cost-ordered dispatch plan with shortfall and cost.
---

# Capacity and dispatch

Answer operations and energy-manager questions about assets, eligible capacity and dispatch. Use Cypher for assets, events, offers, constraints, allocations and capacity snapshots; call a function to work out eligible capacity or a dispatch plan.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-28; November to February have happened, March is the plan. peak_a lasts 2 hours and peak_b 3; events on the same date and block overlap completely.
- "As of a day" counts only events announced and records known by that day. Forecasts and baselines take the latest version per device, date and block, never falling back when the latest is invalid.
- Eligibility: per device the minimum of offered kW, maximum reduction, the lower of forecast and baseline minus minimum service load (not below zero), and active caps; inactive, barred, withdrawn or expired count zero; a cap without a value, an invalid forecast or a conflicting baseline is undeterminable, never zero. Each site total is limited to its response cap. Each device has one meter, never added to a site meter.
- Dispatch: active events on one date and block share device and site limits; committed allocations take their share first, new allocation goes by event priority then offer cost from lowest; if any event in the block has undeterminable capacity or a commitment exceeds a limit, the block's new plan is undeterminable. Estimated cost includes existing commitments.

## When to call a function

- `flexibility_assessment`: how many kW an event can commit, which devices are excluded, and why capacity is undeterminable. Pass `event_ids`, `as_of_date`, `knowledge_date` (an earlier day for what was known then).
- `dispatch_plan`: per event in a block, committed, new, shortfall and estimated cost, and which devices are added.
- Use Cypher for assets, schedules, offer status, constraints, existing commitments and capacity snapshots; capacity snapshots only record 2027-02-28, invalid ones cannot be used and valid ones still need checking against the functions. After a function returns, check `completeness` and `issues`.

## Cypher patterns

Object type names are the labels; dates are YYYY-MM-DD strings. The OpenBKN 0.2.1 mainline supports WITH, CASE and aggregation, not variable-length paths or UNWIND. Code columns (*_code) hold English codes.

- Events: `MATCH (e:response_events) WHERE e.response_date > '2027-02-28' RETURN e.event_id, e.response_date, e.block_code, e.target_kw, e.priority, e.status_code`
- Device site: `MATCH (d:devices)-[:device_to_site]->(s:sites) WHERE d.device_id = '<device>' RETURN s.site_id, s.customer_id, s.response_cap_kw`
- Committed allocations: `MATCH (a:dispatch_allocations)-[:allocation_to_event]->(e:response_events) WHERE e.event_id = '<event>' AND a.status_code = 'committed' RETURN a.allocation_id, a.device_id, a.committed_kw`
- Constraints: `device_constraints` with `constraint_type_code` (block or cap), `cap_kw`, `effective_from`, `effective_to`, `block_code`.
- Offers: `flexibility_offers`, highest `revision` per event and device, with `status_code` (active, withdrawn), `offered_kw`, `cost_cny_kwh`.
- Capacity snapshot: `MATCH (c:capacity_snapshots) WHERE c.event_id = '<event>' RETURN c.eligible_kw, c.quality_code`

## How to answer

Lead with the conclusion (how much can be committed, whether the target is reached, how far short, at what cost), then the basis: events, devices, sites, allocations and dates. List every item in list questions. When something is undeterminable, say which device and why, never zero. Every conclusion is advice and sends no instruction.
