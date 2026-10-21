---
name: retail-investigation-en-us
description: Read-only food traceability, inventory fulfillment, replenishment and recall investigation.
---

Establish business date, knowledge cutoff, product/location and actual stock versus future plan. Discover actual functions/metrics with search_capabilities; never guess IDs. Read the attached business-contract.md first.

1. Use native object queries for master data, inventory_asof for inventory/expiry/quality/trace, fulfillment_plan for shared-stock allocation or replenishment, and recall_assessment for reach/control. Use contract-defined modes, scopes and fields.
2. Check isError, exit_code, nonnull result, completeness and issues. Unknown remains null; snapshots cannot replace failed reconstruction. Paginate complete source lookups; obey actual DATE filter types and do not guess timezone.
3. recorded_available_quantity and recorded_recall_coverage each describe one recorded snapshot instance. Match business/knowledge date, product, location or recall and unit. Never aggregate historical snapshots.
4. Preserve exact Decimal and six-decimal quantities/ratios. Never add incompatible products or units. Delegate deduplication, reversals, late reports and overlapping controls to the public functions.
5. At most one native function per run_code. Project only needed rows, evidence and issues; do not re-embed large previous JSON into source. If multiple functions are needed, call separately. Planned inflow is not realized stock.
6. Explain English business facts while preserving typed status_code values. Cite source IDs, scope, uncertainty and read-only suggestions. Do not place orders, ship goods or send recall notifications.
