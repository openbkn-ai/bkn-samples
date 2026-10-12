# Backward_Plan Contract

Map one forecast or one new customer demand from `product_query` to **Backward_Plan** (`backward_plan`). Resolve a unique product, quantity, deadline and explicit alternate policy. `forecast_id` is optional; preserve its leading zeroes and suffixes. Default `business_date=2026-08-25` and `warehouse_scope=all`. Discover actual MCP parameter names and types rather than assuming a generic operation schema.

The function reads BOM, stock, POs, material lead times and forecast facts. Report its business date, resolved scope, finished stock allocation, net manufacturing quantity, `fulfillment_mode`, customer earliest date/delay, internal risks, shortages and unresolved supply.

`finished_goods` mode skips manufacturing when stock covers demand, but cannot mark a past deadline on time. `production_plan` needs sufficient dated supply and a supported net manufacturing tree. Request `full_tree` only when complete tree evidence is needed. Structural nodes and net manufacturing nodes are different measures.

For a deterministic material supply check, call **Supply_Status** with explicit material, gross quantity, business date and need date. Read `on_time_covered`, `on_time_shortage_qty`, `available_qty`, `on_time_po_qty` and `po_receipts`. Confirmed stock plus valid dated net POs yields a definite yes/no within this closed supply pool; it does not promise unknown future purchases.

Use actual output fields and preserve receipts. Lead_Time and stock coverage provide risk context without replacing a complete backward schedule. Suggestions are for human review only.
