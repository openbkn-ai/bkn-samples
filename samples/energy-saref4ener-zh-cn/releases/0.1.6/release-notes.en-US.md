# 0.1.6: capabilities reorganized around business roles, fully usable on Community

This release follows the new [business PRD](../../docs/PRD.md). The two recorded-snapshot metrics are removed, so the Community edition can use the whole sample; assets, events, receipts, the ledger and snapshots are queried with Cypher. The three native functions `flexibility_assessment`, `dispatch_plan` and `settlement_assessment` stay, with inputs slimmed to events, business date and knowledge date.

The investigation Skill becomes two, "Capacity and dispatch" and "Delivery and settlement", stating for aggregator operations, site energy managers, response duty officers and settlement clerks the business rules, when to use Cypher and when to call a function. The business date, eligible capacity, shared-block dispatch, delivery verification and settlement rules are written into the knowledge network description.

Adds 15 experience cards taken from the new 50-question business-scenario test set. Sample data and the ontology structure are unchanged.

Follow the existing uninstall/install workflow to replace an installed package; uninstall removes the sample's data and owned resources, so preserve any required changes first. Acceptance results are recorded separately and do not guarantee model answer accuracy.
