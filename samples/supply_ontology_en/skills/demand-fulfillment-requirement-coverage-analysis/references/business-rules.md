# Stock and Allocation Rules

Default scope is `all`; honor explicit scopes. `available_inventory_qty` is already net of reservations. Stock is shared across repeated BOM positions, branches and demands.

Allocate finished stock before manufacturing for customer demand. At each level, allocate existing component stock and expand only its net shortage. Manufacturing-only capacity excludes finished goods. Stock-only results exclude POs and new procurement.

Main rows have `alt_priority == 0`, including main rows marked `alt_method=Alternate`. Alternate eligibility is local to product, parent and nonempty group. Use each candidate's own usage ratio, select one candidate per position, and cap coverage at remaining parent demand. Prefer maximum current parent coverage, then the main component, then source row order. Do not mix candidates or reuse stock. Demands follow array order and BOM siblings follow source order. This deterministic policy does not claim a global optimum.

Dated supply counts available stock plus confirmed open net receipts `max(0, qty-actqty)` strictly after the business date and no later than the need date. Overdue, undated, closed and fully received POs cannot establish confirmed on-time supply. PRs explain evidence but are not supply.

Incomplete data or unsupported rules require an explicit limitation. With complete stock-only conditions, give a definite coverage result from final leaf shortages. Read actual published MCP results; never reconstruct the calculation from CSVs, answers or implementation source. No automatic purchase, monitor or ERP writes.
