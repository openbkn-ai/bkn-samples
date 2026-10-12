# Demand_Coverage Contract

For structure-only comparison, resolve at least two different products and use **Shared_BOM**. Return shared codes/count without a coverage or contention claim.

For allocation, require explicit quantities, alternate policy, warehouse scope and input order. Call **Shared_Demand_Allocation** with object-array `demands`. Stock-only defaults exclude POs; dated supply needs explicit supported dates.

Report each demand's finished stock allocation, net manufacturing quantity, coverage and complete shortage list. `report_grain=full` adds material allocation and the remaining shared pool. Preserve actual receipts; do not infer contention by adding independent single-demand results.
