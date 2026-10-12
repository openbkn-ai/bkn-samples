---
name: supply-en-demand-fulfillment-capacity-analysis
description: Current sellable capacity from finished goods and component stock on supply_ontology_en.
---

# Sellable Capacity

Use **Total_Sellable** for a quantity-only question. Use this Skill to explain finished goods, manufacturing capacity and deadline boundaries. Manufacturing capacity excludes finished goods; total sellable combines finished stock with stock-supported manufacturing. Both exclude incoming supply and do not establish a dated delivery promise.

1. Resolve a unique product code and explicitly confirm `substitute_enabled`.
2. Production and finished goods scopes default to `all`; honor explicit scopes.
3. Call **Total_Sellable** through MCP. Use **Manufacturing_Capacity** or **BOM_Stock** to explain bottlenecks.
4. Verify layer-by-layer component deductions, shared stock and resolved scope. Do not substitute a leaf-only minimum calculation.
5. Report `fg_qty`, `theoretical_build_qty`, `total_sellable_qty`, scopes, alternate policy and bottlenecks. Use Backward_Plan for deadline analysis.

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
