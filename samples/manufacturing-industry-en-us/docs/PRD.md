# PRD: End-to-End Manufacturing Planning and Fulfillment Sample

## Business context

Order, material, work-order, execution, quality, and maintenance facts are usually split across ERP, MES, QMS, and equipment systems. Teams can locate each record but struggle to reach an auditable conclusion: whether a customer order's work order was completed under controlled conditions, whether quality supports release, and what is blocking it.

The product provides auditable fact traceability from demand forecast through production plan, material issue, execution, quality, finished-goods receipt, and shipment. It does not replace ERP, MES, or QMS transaction processing.

## Stakeholders and concerns

| Stakeholder | Concern | Required outcome |
|---|---|---|
| Order-fulfillment owner | Whether customer demand has become an executable plan and an eligible shipment | Evidence-backed fulfillment state without manual system joins |
| Production supervisor | Whether completed steps used qualified equipment and people in the right context | Detect completed records with nonconformant conditions |
| Quality owner | Whether final inspection supports release | Inspection state and specification result linked to the work order |
| Materials owner | Whether issued material covers demand | Coverage, uncovered quantity, and completion impact |
| Data/ontology owner | Whether concepts and conclusions are reusable and explainable | Shared objects, relationships, and source semantics |

## Decisions and P0 scenarios

The sample supports: forecast-to-plan traceability; plan-to-work-order traceability; material issue from receipt and inventory location to work-order requirement; execution conformance from machine capability, operator qualification, work center, and scheduled shift date; reusable final-quality specifications and inspection results; finished-goods receipt; and shipment eligibility. Each scenario returns evidence, failure reasons, or an unknown/pending/blocked result.

## Sample business scope

The scenarios use three connected business domains:

- **Master data:** sites, work centers, products, BOMs, routings, equipment, capabilities, people, and shifts.
- **Demand and supply:** customers, sales orders, forecasts, production plans, suppliers, purchasing, receipts, inventory locations, material issues, finished-goods receipts, and shipments.
- **Production operations:** work orders, material requirements, operations, steps, staffing, execution records, quality specifications and inspection, and maintenance.

The sample planning horizon runs from November 2026 through March 2027 and uses date-only business facts. Its released plan snapshot is dated 2026-10-20; its transaction-derived inventory snapshot is dated 2027-03-31. Keeping these facts separate prevents hindsight from being presented as knowledge available when the plan was released.

## Success criteria

Users trace forecast → plan → order → material issue → execution → quality → finished-goods receipt → shipment in one sample; every conclusion is auditable; completed status cannot mask execution nonconformance; shipment requires accepted inspection and finished-goods receipt; and Chinese and English return the same facts.

## Boundary

The sample answers whether a demand-backed work order has planned supply, sufficient issued material, conformant execution, accepted final quality, finished-goods receipt, and an eligible shipment. It does not optimize schedules, calculate ATP, model lot genealogy, or perform root-cause workflows. Those capabilities need finite capacity, customer allocation rules, lot/serial genealogy, and nonconformance workflows. It does not replace transaction systems or present IOF coverage instances as enterprise facts.

## Relationship to solution design

This PRD defines business needs and outcomes. The model, IOF mapping, metrics, functions, Skill, tests, and installation are solution responses that must demonstrate P0 satisfaction; technical feasibility does not enlarge business scope.
