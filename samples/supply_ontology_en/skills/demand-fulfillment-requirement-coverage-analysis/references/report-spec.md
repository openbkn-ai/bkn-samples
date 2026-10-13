# Demand_Coverage Report

Report network, policy, resolved scope and allocation order. For structure-only questions, show shared codes/count and state that structural overlap is not contention or coverage.

For quantified demands, show overall demand count, uncovered products and shared shortages, then each demand's quantity, finished allocation, manufacturing remainder, coverage and shortages. Distinguish stock-only from explicitly supported dated PO supply. If truncated, state “showing N of X items”; never present a partial list as complete.

For full diagnosis, show gross quantity, allocated stock, shortage, shared-material flags and remaining stock from `report_grain=full`. Recommend only `recommended_replenishment_qty` for the current demand snapshot. Do not invent MOQ or safety stock. Human users may rerun with different priority or quantity; never place a PO automatically.
