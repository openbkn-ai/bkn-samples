# Stock and Allocation Rules

Default scope is `all`; honor explicit scopes. `available_inventory_qty` is already net of reservations. Stock is shared across repeated BOM positions, branches and demands.

Allocate finished stock before manufacturing for customer demand. At each level, allocate existing component stock and expand only its net shortage. Manufacturing-only capacity excludes finished goods. Stock-only results exclude POs and new procurement.

Main rows have `alt_priority == 0`, including main rows marked `alt_method=Alternate`. Alternate eligibility is local to product, parent and nonempty group. Use each candidate's own usage ratio, select one candidate per position, and cap coverage at remaining parent demand. Prefer maximum current parent coverage, then the main component, then source row order. Do not mix candidates or reuse stock. Demands follow array order and BOM siblings follow source order. This deterministic policy does not claim a global optimum.

Dated supply counts available stock plus confirmed open net receipts `max(0, qty-actqty)` strictly after the business date and no later than the need date. Overdue, undated, closed and fully received POs cannot establish confirmed on-time supply. PRs explain evidence but are not supply.

Incomplete data or unsupported rules require an explicit limitation. With complete stock-only conditions, give a definite coverage result from final leaf shortages. Read actual published MCP results; never reconstruct the calculation from CSVs, answers or implementation source. No automatic purchase, monitor or ERP writes.

# Backward Dates and Customer Coverage

Use calendar days and default business date `2026-08-25`. Schedule need dates backward from the deadline using fixed lead times; a child is needed one day before its parent's start. Purchased/Subcontracted use purchase lead time; Manufactured uses production lead time. Missing data must not silently become a confirmed zero-day lead time. Do not compress remaining manufacturing to one day merely because some stock exists or MRP is absent.

Customer availability must account for remaining parent manufacturing stages. An isolated material lead time or extreme PO date is not a complete product schedule. Accumulate dated supply until the required quantity is covered. Unknown future receipts and unsupported manufacturing schedules do not establish a definite commitment.

If finished goods cover demand and the deadline is not before the business date, the static sample can establish stock coverage. A past deadline is not on time. Keep customer delay separate from internal A/B risks. Work calendars, real capacity, transport and approved transfers are outside this fixture. Report actual alternate scheduling support rather than inferring it from an enabled flag.
