# Precision machining order fulfilment: planning, production, quality and purchasing PRD

## Business goal and users

A fictional precision machining company machines pump housings, valve bodies, impellers and flanges for ten customers in two plants, Shenzhen and Suzhou. Orders, material, production execution, quality and maintenance records sit in different systems. Business users need to ask in plain business language whether orders will ship on time and what is holding them up, whether finished work was done under compliant conditions, whether inspection supports release, and which purchases and machines will affect upcoming production, and see the orders, work orders, issues, executions, inspections and shipments behind every conclusion.

| User | Questions | Expected conclusion |
|---|---|---|
| Order fulfilment manager | Which orders are short or late and why; can the March orders start | Units owed, days late, blocking causes, replacement work orders |
| Production lead | Work order progress, output and scrap; were executions done by qualified machines and people on their scheduled shifts | Work order status, yield, non-compliant executions and why |
| Quality manager | Does inspection support release; was anything released out of specification | Rejected lots, out-of-limit characteristics, quality escapes, specification revisions |
| Purchasing and materials manager | Is material sufficient; which purchases are overdue or rejected; was anything issued improperly; what stock is left | Shortages, overdue purchases, rejected receipts, issues from receipts in inspection, available stock |

Success: users get conclusions and evidence that follow these rules without stating any calculation rule in the question. An answer that is right only when the rule is spelled out in the question, and wrong when it is phrased differently, does not count.

## Decision scope

In scope: plants, work centres, products, BOM revisions, routings, machines and capabilities, operator qualifications and shifts, customers and sales orders, demand forecasts and production plans, work orders and material requirements, purchasing and receipts, material issues, execution records, inspection lots and results, quality specifications, finished goods receipts, shipments, inventory and machine maintenance.

Out of scope: placing real orders, scheduling, dispatching, releasing or shipping; finite-capacity scheduling and optimal sequencing; cost and price; lot and serial genealogy; nonconformance disposition. Every conclusion is advice only.

## Business rules

These are the defaults, and users need not repeat them; when a user states a different condition, follow the user.

1. **Business date**: 2027-02-28. "Now", "today" and "currently" mean this date. Records from November 2026 to February 2027 have happened; March work orders are the plan; inventory is the 2027-02-28 snapshot.
2. **Orders and delivery**: each sales order line is produced by a work order; when a work order's inspection is rejected, a replacement work order can remake the same order line. Units owed = ordered − shipped; above zero means the line is short. Once a line is fully shipped, it is late if its last shipment is after the requested date, and days late = last shipment date − requested date; a line still not fully shipped after its requested date is also late.
3. **Material requirement and availability**: requirement = work order quantity × quantity per × (1 + scrap factor), rounded up. Material is complete when the issued quantity is at least the requirement. Material may be issued only from accepted receipts; issuing from a receipt still in inspection or rejected is an improper issue.
4. **Can a work order start**: its BOM revision is frozen and all material is complete by the planned start date (the production plan line's planned start date). A work order is blocked when its BOM is not frozen, or when the planned start date has arrived and any material is incomplete; say which. A work order whose planned start has not arrived and has no material issued yet is not blocked.
5. **Execution compliance**: every started execution must meet all four conditions; failing any one makes it non-compliant:
   - the machine has the capability the step requires, with a qualified capability status;
   - the machine has no maintenance work order on the execution's start date;
   - the operator holds a qualified qualification for that capability, valid on or after the start date;
   - the operator is assigned, in the shift covering the start date's week, to the work centre of that operation.
6. **Output and yield**: work order completed quantity = good quantity of the last operation; operation yield = good ÷ (good + scrap); work order yield = completed quantity ÷ work order quantity.
7. **Quality release**: a final inspection lot passes only if it is accepted and every measured value lies within the referenced specification's limits (inclusive). A result recorded as pass with a value outside the limits counts as a failure and is a quality escape. Judge each result against the specification revision it references; for a product's current specification use the one whose status is active.
8. **Finished goods and shipment**: only accepted finished goods receipts can ship; shipped quantity never exceeds the received or ordered quantity.
9. **Purchasing and receipts**: receipts are measured against the purchase order's expected receipt date; a receipt after it is late. A purchase order whose expected date is before the business date and whose accepted quantity is still below the ordered quantity is overdue. Rejected receipts do not count as received.
10. **Inventory**: available = on hand − allocated. Stock in the inspection hold cannot be issued.
11. **Maintenance**: a maintenance work order planned before the business date and not completed is overdue; a machine under repair cannot be scheduled.
12. **Forecast and plan**: production plans are summed by the month of each work order's due date and compared with that month's forecast; plan coverage = planned quantity ÷ forecast quantity.

## Business scenarios

| Scenario | User question | Expected conclusion |
|---|---|---|
| S01 Products and capacity | What do we make, from what material, through which operations, with which machines and people | BOMs, routings, machine capabilities, operator qualifications |
| S02 Orders and delivery | What do we owe customers, which orders are late, by how long | Units owed, days late, split shipments, replacement work orders |
| S03 Forecast and plan | Does the plan cover the forecast | Coverage per product and month, under-planned products |
| S04 Material availability | Is material sufficient; which work orders are blocked by material or BOM | Requirements, shortages, blocking causes |
| S05 Purchasing and receipts | Which purchases are overdue, rejected or late; was anything issued improperly | Overdue purchases, rejected receipts, late suppliers, issues from receipts in inspection |
| S06 Progress and output | How far has each work order got; how much output and scrap | Work order status, completed quantity, yield, scrap operations |
| S07 Execution compliance | Was finished work done under compliant conditions | Non-compliant executions and why, affected work orders and operators |
| S08 Quality release | Can inspection support release; were there escapes | Rejected lots, out-of-limit characteristics, quality escapes, specification revisions |
| S09 Maintenance | Which services are overdue; which machines cannot be used | Overdue maintenance, machines under repair, maintenance clashing with production |
| S10 End-to-end trace | What happened to an order from receipt to shipment | Order → work order → issue → execution → inspection → receipt → shipment |

## Acceptance

1. 50 questions per language covering the 10 scenarios above: 12 basic, 20 medium and 18 complex, all asked in business language without calculation rules in the question.
2. Each complex question involves at least two business rules or reasoning across three or more kinds of records.
3. Reference answers are computed independently of the capabilities under test, and the tested side never sees them.
4. One round per language, targeting 100% accuracy.
