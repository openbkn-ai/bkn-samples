# Food Supply Operations: Lot Traceability, Inventory Fulfilment and Recall PRD

## Goals and users

A food retailer runs 25 warehouses and 25 stores selling dairy, bakery, beverages, cereals and snacks. Lots arrive from suppliers, are inspected and received, move between warehouses and stores, and are sold or returned at stores; quality problems trigger recalls. Business users want to ask in plain business language where stock is, whether it can be used, whether it is enough and how far a recall reaches, and see the lots, events and dates behind every conclusion.

| User | Concern | Expected conclusion |
|---|---|---|
| Quality lead | Which lots failed inspection or are recalled, where the stock is, how much was sold, how much is under control | inspection results, quarantined and recall-blocked quantities, flows, units sold and not returned, coverage |
| Warehouse and distribution lead | How much is really available, whether orders can be filled, how much to replenish in March | available stock with the reasons it is reduced, line-by-line allocation and shortfalls, replenishment against the forecast |
| Store manager | How much the store can sell, what is near or past expiry, which orders a recall affects | store availability, near-expiry and expired lots, affected orders |

Success means users get conclusions that follow the business rules below without stating any calculation rule, together with the lots, events and documents behind them. An answer that is only right when the rule is spelled out in the question, and wrong when it is phrased differently, does not count.

## Decision scope

In scope: product, organization and location master data; lots and inspections; receipts, transfers, in-transit, sales, returns and other stock movements; holds; orders and reservations; demand forecasts and planned receipts; lot splits and transformations; recalls, recall snapshots and inventory snapshots.

Out of scope: placing orders, shipping or paying; routing; forecasting models; automatic recall notices; regulatory certification and financial settlement. Every conclusion is advice only.

## Business rules

These are the default rules; users do not need to repeat them. When a user states a different condition, the user's condition wins.

1. **Business date**: 2027-02-28; "now" and "today" mean this date. March forecasts and planned receipts are the plan known today and never count as having happened.
2. **As of a day**: count only actual events dated on or before that day and recorded on or before that day; an event recorded later does not count when looking at what was known before it was recorded.
3. **Event trust**: an event recorded twice counts once; a reversed event does not count. When copies of one event conflict, an arrival has no matching dispatch, stock goes negative, or returns exceed sales, the stock of the affected lot-location cannot be determined, and it is never treated as zero.
4. **Quantities**: always in the product's base unit (units); quantities recorded in cases are multiplied by units per case.
5. **On hand and in transit**: receipts, production, arrivals and returns add to on hand; sales, consumption and dispatches reduce it; dispatched goods not yet arrived are in transit, not on hand.
6. **Quarantine**: a lot that failed inspection or is still awaiting it is fully quarantined; returns and active holds are quarantined too, and the same units are never deducted twice.
7. **Recall block**: an open recall reaches every downstream lot from its root lot through splits and transformations; whatever on-hand stock of those lots is not already quarantined is blocked. A closed recall no longer blocks anything.
8. **Available stock**: on hand minus quarantine, recall block and active reservations; an expired lot has zero available; a reservation can only reduce availability to zero, and anything beyond that is over-reservation. A lot expiring within two weeks is near expiry.
9. **Order allocation**: open orders share one pool of available stock in order of priority, due date and order number. Each line uses only lots at the same location for the same product that passed inspection and remain in date at the later of today and the due date plus the line's minimum remaining shelf days, earliest expiry first; an order's own reservation can be used for that order. Open orders already past their due date are still allocated.
10. **Replenishment**: walk the March forecast in date order, drawing on available stock and on eligible planned receipts arriving by each demand date, earliest expiry first; stock that no longer meets the remaining shelf life on the demand date does not count. The shortfall is the recommended replenishment.
11. **Recall control**: by product and location. Controllable = on hand + in transit of the affected lots; controlled = the quarantined part of it; coverage = controlled ÷ controllable. When controllable is zero or stock cannot be determined, coverage cannot be calculated, which is not zero. Units sold are net of returns and shown separately.

## Business scenarios

| Scenario | User question | Expected conclusion |
|---|---|---|
| S01 Products and locations | What we sell, who supplies it, how many warehouses and stores | products and categories, suppliers, packaging, shelf-life requirement, location counts |
| S02 Receipt and inspection | Which lots failed or are awaiting inspection, where they are | inspection results, stock of problem lots, whether they can be sold |
| S03 Lot flow | Where stock came from, where it went, what it was split into | movement events, transfer sources, split child lots, locations a recalled lot reached |
| S04 Stock and in transit | How much is really available, why it is less | available, in-transit and quarantined quantities, reasons by lot |
| S05 Expiry | What is near or past expiry and still on hand | near-expiry and expired lots, expired quantity |
| S06 Order fulfilment | Whether orders can be filled, how much is short | line allocation, lots used, short orders and shortfall |
| S07 Replenishment | How much to replenish in March, from which demand it falls short | forecast, replenishment, shortfall by demand date, largest gap |
| S08 Recall reach | Which lots, locations and orders a recall reaches | downstream lots, stock by location, sold and not returned, affected orders |
| S09 Recall control | How much is controlled and how much is left | controlled, controllable, coverage, uncontrolled quantity, handling of closed recalls |
| S10 Data trust and look-back | Which data is unreliable, how conclusions differ by date | undeterminable stock and reasons, duplicate and reversed events, before and after late records |

## Acceptance

1. 50 questions per language covering the 10 scenarios: 12 basic, 20 medium, 18 complex. All asked in the business language of the quality, warehouse or store lead, with no calculation rule in the question.
2. Complex questions involve at least two business rules, or reasoning across three or more record types.
3. Reference answers are computed independently of the capability under test, and the tested agent never sees them.
4. One round per language, with a 100% accuracy target.
