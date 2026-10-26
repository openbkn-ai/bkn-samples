---
name: supply-en-demand-fulfillment-requirement-coverage-analysis
description: Shared_BOM structure and stock allocation across multiple demands on supply_ontology_en.
---

# Demand_Coverage

Use this Skill for at least two demands. For one fixed demand, call **Demand_Coverage** directly.

1. Resolve unique product codes. If all quantities are missing, use **Shared_BOM** for structure only; it requires at least two different products.
2. Complete any missing quantities and confirm alternate policy, scope and allocation order. A missing quantity is not zero.
3. Default to all warehouses and current stock only. Do not add undated POs to the shared pool.
4. Call **Shared_Demand_Allocation** with `demands: [{"product":"code","qty":quantity}, ...]`. Array order is allocation priority; honor explicit priorities and preserve input order for ties.
5. Verify finished-stock-first, component-first deductions and a shared pool across branches and demands. Separate single-demand results cannot establish multi-demand contention.
6. Report each demand's coverage, finished stock allocation, remaining manufacturing quantity, shortages, scope and order. If truncated, state the displayed and total counts.
7. Base replenishment solely on `recommended_replenishment_qty`. Do not invent MOQ, safety stock or unrelated demand, or create business records.

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

## Single-demand material assurance

For the stock-only Workshop material-assurance case, use `material_coverage` with an explicit `demand_purpose`: `customer_delivery` allocates finished goods first; `new_production` excludes them. Read the published tool metadata to select its localized name. Return the bounded covered/uncovered quantities, all material gaps, source BOM version and collection provenance. `replenishment_draft` accepts the prior complete coverage result and checks its structure only; it does not re-query facts and returns a proposal only; it does not persist, place purchases or promise delivery. Do not equate a saved-looking draft ID with a stored business record. This path handles one demand; use shared contention for multiple demands.
