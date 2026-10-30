# Farm Machinery and Drone Supply Chain: Order Fulfilment, Material Assurance and Purchase Follow-up PRD

## Goals and users

A manufacturer of BeiDou navigation autopilots, vehicle terminals, agricultural drones and smart monitoring systems wants planners and buyers to get delivery and material answers by asking in plain business language. There are two core users:

- **PMC production planning manager**: when backlog owed to customers can be cleared; whether a new order can be accepted and how much; whether materials cover a work order; how much to prepare for forecasts.
- **Purchasing manager**: which materials block production; which open purchases to expedite and with which supplier; which materials have nothing on order and must be ordered now, and the earliest arrival.

Success means users get conclusions that follow the business rules below without stating any calculation rule, together with the orders, stock, BOMs and purchase records behind them. An answer that is only right when the rule is spelled out in the question, and wrong when it is phrased differently, does not count.

## Decision scope

In scope: finished-goods and material master data, multi-level BOMs and alternates, real-time stock by warehouse, sales order signing and shipping, demand forecasts, MRP planned orders, purchase requisitions, purchase orders and receipts, production work orders.

Out of scope: actually placing orders, shipping, scheduling or closing documents; transit time; capacity and labour scheduling; prices and costing; training forecast models. Every conclusion is advice and commits nothing.

## Business rules

These are the default rules; users do not need to repeat them. When a user states a different condition, the user's condition wins.

1. **Business date**: 2026-08-25. "Now", "today" and "current" all mean this date; the data snapshot date is 2026-08-13.
2. **Available stock**: only the available quantity of stock with status Available counts; Defective stock cannot be used in production or shipped. By default every warehouse in the company counts. "Finished-goods warehouses" means Suzhou Finished Goods, Urumqi Finished Goods and Harbin Finished Goods; "the seven Suzhou plant production warehouses" means Suzhou Subassemblies, Suzhou Finished Goods, Suzhou Electronics, Suzhou Drone Materials, Suzhou Assembly, Urumqi Finished Goods and Harbin Finished Goods.
3. **Backlog**: a sales order whose signed quantity exceeds its shipped quantity is owed; owed orders whose promised date is before the business date are overdue. Owed orders are filled by promised date, then by order number.
4. **Open purchases**: a purchase order line that is neither closed nor terminated and whose ordered quantity exceeds its received quantity. Lines due on or after the business date count as supply on their due date; "the next N days" means the day after the business date through day N inclusive. Lines due before the business date are overdue: the supplier missed the date, so they are not firm supply. They are listed for expediting and count only when the user explicitly assumes they can be chased in.
5. **New orders**: a bought-in part ordered today arrives after its standard purchasing lead time, counted from the business date.
6. **Buildable quantity**: use finished-goods stock first, then expand the BOM level by level for the rest; at each level, use that component's available stock and expand only the net shortage. Shortages of materials that cannot be expanded further are the real shortages. Several demands share one stock pool, and the same stock cannot be used twice. By default no alternates are used and no new purchases are counted.
7. **Planning with open purchases**: "now" or "with current stock" means stock only; for issues or deliveries by a date, supply is stock plus open purchase lines due by that date (inclusive). Overdue lines follow rule 4.
8. **Alternates**: when the user allows alternates, each position in an alternate group uses one material only, never a mix; each material uses its own usage quantity; the material that covers more demand wins, and the main part wins a tie.
9. **Available to promise**: finished-goods stock plus what current stock can still build, minus the product's signed backlog; what remains can be promised to new orders. "Stock on hand" means finished-goods stock only, not what can still be built.
10. **Forecasts**: a forecast whose close status is not Closed is open. Forecasts are met after signed backlog; how much forecast current stock can support is its available to promise.
11. **Document trace**: a purchase order line maps to its requisition line by source requisition line and material; a requisition line maps to the MRP planned order that generated it; an MRP planned order maps to its root forecast. One forecast can cover several products.

## Business scenarios

| Scenario | User question | Expected conclusion |
|---|---|---|
| S01 Products and materials | What do we sell, how many suppliers, how long to buy a part | models, product lines, supplier count, purchasing lead time |
| S02 Backlog | How much we owe, how late, what can't be covered | owed orders, days overdue, backlog by customer and salesperson, products neither stock nor production can cover |
| S03 Forecasts and preparation | How heavy forecast pressure is, how much we can support | open forecasts, forecast-to-stock ratio, products with no stock, supportable quantity after backlog |
| S04 BOM and common parts | What a material affects | first-level materials, where-used, common parts, shortage impact |
| S05 Stock | What we can ship, what is unusable | finished-goods warehouse stock, material stock, defective stock |
| S06 Order acceptance | Can we accept, how much, what blocks it | available to promise, plant vs company difference, blocking materials and complete date, effect of open purchases |
| S07 Backlog filling and competing orders | Who first, what if orders arrive together | unfilled orders, shortages with shared stock and open purchases |
| S08 Purchase follow-up | What arrives today, whom to chase, what to order | open and overdue purchases, today's and this month's arrivals, key suppliers, buyer workload, shortages to expedite or order |
| S09 Lead time and dated supply | Earliest arrival, enough by a date | new-order arrival, bottleneck after alternates, supply by date with open purchases, buildable after chasing overdue purchases |
| S10 Plan execution and trace | Is the plan executed, what was bought for whom | unreleased MRP orders, incomplete work orders, shortages before start, purchase-to-forecast trace |

## Acceptance

1. 50 questions per language covering the 10 scenarios: 12 basic, 20 medium, 18 complex. All asked in the business language of a PMC or purchasing manager, with no calculation rule in the question.
2. Complex questions involve at least two business rules, or reasoning across three or more document types.
3. Reference answers are computed independently of the capability under test, and the tested agent never sees them.
4. One round per language, with a 100% accuracy target.
