---
name: supply-en-sales-signing-calendar-month-analysis
description: Complete calendar-month sales signing comparisons on supply_ontology_en through MCP, with adjacent-month arithmetic in the agent.
---

# Monthly Sales

Analyze signing quantities, not shipping events, stock history or production lead times.

1. Distinguish complete calendar months from same-date month-to-date comparisons. Confirm year, months and business timezone; the sample uses `Asia/Shanghai`.
2. Discover `supply_ontology_en_salesorder`, its `signing_date` and `signing_quantity` properties, and **Signing Events** through MCP. Use actual published IDs.
3. Resolve any product filter and use the same product/status filters for every month. Current shipped totals cannot establish monthly shipping events.
4. Query each complete business month with `signing_date >= first day 00:00` and `signing_date < next month's first day 00:00`, converted from the business timezone. Months have different lengths; May has 31 days. Handle December rollover, February and leap years.
5. Use metric `time: {instant: true}` with explicit date conditions. Discover the actual AND syntax, timestamp unit, tool name and parameters. Do not attach `sameperiod` to this path.
6. Query the complete previous month for the first reported month. April–June therefore requires March–June. Verify each monthly total, then calculate change = current - previous. If requested, calculate growth = change / previous × 100%. Growth is undefined when previous = 0.
7. Null, missing values, failed tools, incomplete pagination and unexplained groups are not zero. Confirm an empty month through an actual object query before reporting zero. Fetch every page when raw rows are required.
8. Report timezone, half-open boundaries, queried totals, adjacent changes and formulas. Keep MCP receipts and recovery evidence.

Existing supply functions analyze BOMs, stock, coverage and backward plans; they do not calculate business-month windows. Do not use Lead_Time for month arithmetic, read CSVs/answers or reconstruct production functions. Calculate simple differences from queried facts in the agent. This Skill embeds no monthly totals or answers.

Acceptance requires discovering and reading this published Skill through MCP, inspecting actual date ranges and verifying totals and arithmetic. CLI success alone does not prove the agent path. Record `sameperiod` diagnostics separately.
