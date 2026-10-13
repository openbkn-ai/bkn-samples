---
name: supply-en-production-schedule-backward-planning
description: Demand deadlines, backward production plans and dated supply risks on supply_ontology_en.
---

# Backward_Plan

Business scenario: deadline coverage for a forecast or new customer demand. Preferred metric: supply coverage and dated receipts. Preferred function: **Backward_Plan**. For a single material's standard lead time, use **Lead_Time**. For current sellable stock, use Sellable Capacity. Without a deadline, do not conclude on-time delivery. Analyze without creating a monitor. This Skill creates no monitor and writes nothing to ERP.

1. Confirm a unique product, quantity, deadline, alternate policy and business date. The default business date is `2026-08-25`; server time is audit information only.
2. Default scope to `all`, honoring explicit scopes. Call **Backward_Plan**. For an existing forecast, pass the exact `forecast_id`, preserving leading zeroes and suffixes; the function reads and validates its facts.
3. Allocate finished stock first, then component stock at each level. Plan only the net manufacturing quantity; do not expand stock-covered branches as manufacturing demand.
4. Finished stock proves current quantity coverage; a deadline before the business date cannot be on time. Manufacturing dates require net demand and sufficient dated supply throughout the chain. One lead time or an extreme PO date cannot substitute for the product date.
5. Flag overdue receipts and unsupported or unknown supply, manufacturing dates, lead times and alternate scheduling. Do not manufacture a definite delivery commitment from incomplete facts.
6. Separate customer earliest availability/customer delay from internal A/B risks. Report business date, scope, alternate applicability and PO quantity/date evidence. Identify excluded real-world capacity, work calendars, transfers and transport.

Inputs: unique product, `demand_qty`, `demand_end`, explicit `substitute_enabled`; optional `forecast_id`; default `business_date=2026-08-25` and `warehouse_scope=all`. Use `report_grain=full_tree` only when a complete supported net manufacturing tree is needed. Distinguish structural BOM nodes from actual manufacturing demand.

## Business rules

- Default warehouse scope is `all`. Honor and report an explicit preset or warehouse list. `all` means unrestricted warehouses, not zero warehouses.
- Use `available_inventory_qty` without subtracting reservations again. Each material shares one physical stock pool across BOM positions and demands.
- For customer demand, allocate finished stock first. Manufacture only the remainder. At each component level, allocate stock before expanding the remaining quantity. An intermediate component shortage is not a final leaf shortage.
- Alternate eligibility belongs to a BOM position: product, parent and group. Use each candidate's own usage ratio. Never reuse stock or propagate eligibility between positions. Later demands choose candidates again from the remaining pool. Do not assume mixed candidates can jointly cover one position.
- Stock-only analysis excludes POs. Dated supply requires explicit business and need dates. Net unreceived quantity is `max(0, qty-actqty)`. Count only confirmed open receipts strictly after the business date and no later than the need date; exclude closed, overdue, undated and fully received rows from confirmed coverage.
- Incomplete facts, unfinished pagination, missing lead times or unsupported business rules require an explicit limitation. Successful execution alone does not establish business correctness.
- Discover parameters and use actual published MCP results. Do not read CSVs, answer sets, implementation source or a direct database to reproduce the calculation. Never guess unsupported parameters.

## Deterministic coverage

For a fully specified stock-only question with alternatives and purchases disabled, give a definite yes/no from final leaf shortages. Expand intermediate net shortages first. Multiple demands share stock in input order. Structural overlap does not imply actual contention. For a material with explicit business date, need date and confirmed supply pool, use the on-time coverage fields without speculating about future purchases.

See `references/` where provided for inputs, evidence and reporting.
