---
name: supply-en-demand-fulfillment-risk-summary
description: Summarize verified stock, allocation and dated supply risks on supply_ontology_en.
---

# Supply Risks

Read-only summary of verified stock, net demand, procurement and alternate results.

1. Confirm unique product, customer demand versus manufacturing-only demand, quantity, need date and alternate policy. Honor explicit warehouse scope; default to all and business date `2026-08-25`.
2. Query finished stock and demand coverage. Confirm finished-goods-first and component-first allocation through one shared pool. Manufacturing-only demand must explicitly exclude finished goods.
3. Inspect supply and alternate candidates for uncovered materials. Read every candidate's facts even when alternatives are disabled; unread stock is not zero. Eligibility is specific to product, parent and group.
4. Allocate dated net receipts against the need date. Overdue POs require confirmation. Standard lead time does not prove that current net demand needs new purchases.
5. Separate stock-covered demand, definite shortages and unresolved receipt/manufacturing timing. Keep quantity coverage distinct from a deadline promise; report source, scope, dates and completeness.

Use published MCP facts and functions only. Do not reproduce algorithms from CSVs, answer sets or implementation source. Record unsupported premises rather than inventing causes. Create no purchase, monitor or other business record.

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
