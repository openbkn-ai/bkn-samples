# 0.1.11: capabilities rebuilt around PMC and purchasing scenarios, fully usable on Community

This release follows the new [supply chain PRD](../../docs/PRD.en-US.md). All metrics and metric-based logic properties are removed, so the Community edition can use the whole sample. Lookups, totals and relations are answered with Cypher. The 17 functions become two calculation functions, `Buildable_Quantity_and_ATP` (buildable quantity and available to promise) and `Demand_Coverage_and_Shortages`, which can add open purchases due by a date, assume overdue purchases are chased in, and protect signed backlog first. The buildable-quantity function takes several products in one call.

The shortage-rule event, the replenishment draft action, and the monitoring task, monitoring evidence and requisition decision objects that had no supporting data are removed. The five Skills become two, "PMC production planning" and "Purchase follow-up", stating the business rules, when to use Cypher and when to call a function. The business date, backlog, open purchase and available-to-promise rules are also written into the knowledge network descriptions.

The experience set now has 15 cards taken from the new 50-question business-scenario test set, covering backlog, stock, forecasts, common parts, purchase follow-up, document trace, order acceptance and blocking materials. Sample data is unchanged.

Follow the existing uninstall/install workflow to replace an installed package; uninstall removes the sample's data and owned resources, so preserve any required changes first. Acceptance results are recorded separately and do not guarantee model answer accuracy.
