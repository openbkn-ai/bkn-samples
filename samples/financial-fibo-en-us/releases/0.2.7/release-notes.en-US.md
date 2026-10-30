# 0.2.7: capabilities reorganized around business roles, fully usable on Community

This release follows the new [business PRD](../../docs/PRD.md). The two recorded-snapshot metrics are removed, so the Community edition can use the whole sample; lookups, traces and month-end snapshots are answered with Cypher. The three native functions `settlement_asof`, `valuation_asof` and `limit_assessment_asof` stay, recomputing from the original records for a given date and what was known that day; the multi-date batch input is removed, so each call covers one dated scope.

The investigation Skill becomes two, "Post-trade operations" and "Risk and limits", stating for middle office, accounting, risk and portfolio-manager questions the business rules, when to use Cypher and when to call a function. The business date, settlement status, price eligibility, concentration, counterparty receivable and limit-effectiveness rules are written into the knowledge network description; Cypher patterns stay within what OpenBKN 0.2.1 supports.

Adds 15 experience cards taken from the new 50-question business-scenario test set, covering settlement, valuation, concentration, counterparty receivables, future limits and look-back. Sample data and the ontology structure are unchanged.

Follow the existing uninstall/install workflow to replace an installed package; uninstall removes the sample's data and owned resources, so preserve any required changes first. Acceptance results are recorded separately and do not guarantee model answer accuracy.
