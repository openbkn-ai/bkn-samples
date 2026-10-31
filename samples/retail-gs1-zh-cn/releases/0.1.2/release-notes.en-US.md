# 0.1.2: capabilities reorganized around business roles, fully usable on Community

This release follows the new business PRD. The two recorded-snapshot metrics are removed, so the Community edition can use the whole sample; lookups, traces and the February 28 inventory and recall snapshots are answered with Cypher. The three native functions `inventory_asof`, `fulfillment_plan` and `recall_assessment` stay for event replay, order allocation and replenishment, and recall tracing; each now declares only the inputs it uses, with descriptions per language.

The investigation Skill becomes two, "Inventory and fulfilment" and "Quality and recall", stating for warehouse, store and quality-lead questions the business rules, when to use Cypher and when to call a function. The business rules are written into the knowledge network description.

Adds 15 experience cards taken from the new 50-question business-scenario test set, covering inspection, stock and its reasons, expiry, orders, replenishment, lot flow, recall reach and control, and data trust. Sample data and the ontology structure are unchanged.

Follow the existing uninstall/install workflow to replace an installed package; uninstall removes the sample's data and owned resources, so preserve any required changes first. Acceptance results are recorded separately and do not guarantee model answer accuracy.
