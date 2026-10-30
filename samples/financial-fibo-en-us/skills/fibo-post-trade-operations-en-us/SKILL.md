---
name: fibo-post-trade-operations-en-us
description: >
  Use for middle-office and fund-accounting questions on knowledge network financial_fibo_en_us:
  trades and settlement instructions, settlement status, failed and overdue settlements, position
  quantities and cost, realized P&L, prices and FX, market value calculation, blocked valuations
  and month-end reconciliation.
---

# Post-trade operations

Answer middle-office and accounting questions about settlement, positions, valuation and month end. Use Cypher for lookups, totals, relations and month-end snapshots; call a function for a date that is not a month end or for what was known on an earlier day.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-28; "now" and "today" mean this date. November to February are actual; March is the plan. Never present plan data as something that has happened.
- "The situation on a day" counts only records dated on or before that day whose known_date is also on or before that day.
- Settlement: events are incremental and add up per instruction. Settled when the total equals the required quantity; otherwise failed if the latest event failed, partial if some quantity settled, pending if none. Outstanding past the due date is overdue, reported separately from failed.
- Positions: trade-basis and settled-basis quantities are measured separately; unsettled_delta is the difference. Cost is weighted average; realized P&L is in local currency, and different currencies are not added together.
- Valuation: only an approved price at most 3 calendar days older than the valuation date and the single FX rate for that day. A stale, unapproved or missing price blocks the valuation; never substitute an older price. Local value = quantity × price × multiplier (1 for equities, 0.01 for bonds), to the cent; USD value = local value × FX, to the cent.
- Unknown is not zero: with a blocked valuation the portfolio total is unknown; the other securities' amounts can still be given.
- Month end: totals by trade month and local currency, buys positive and sells negative; unsettled sale notional (remaining quantity × execution price × multiplier, local currency) is shown separately.

## When to call a function

- `settlement_asof`: settlement status, remaining quantity, overdue and failed for a day other than February 28, or based on what was known on an earlier day. Pass `portfolio_ids`, `as_of_date`, `knowledge_date` (the same as `as_of_date` for "as known that day") and `view_kind` (actual or planned).
- `valuation_asof`: positions, cost, P&L or market value on a date that is not a month end, or explaining a cost change from the original trades.
- Today's (February 28) settlement status and month-end positions and valuations can be read with Cypher: the month-end snapshots match recomputation from the original records.
- After a function returns, check `completeness` and `issues`; a failed call never means there are no records.

## Cypher patterns

Object type names are the labels, e.g. `settlement_events`, `valuation_snapshots`. Dates are YYYY-MM-DD strings that compare as text. Joins, aggregation (count, count DISTINCT, sum) and ORDER BY are supported. To stay compatible with OpenBKN 0.2.1, do not use WITH, CASE, functions such as coalesce, relationship variables, whole-node returns, property-to-property comparisons, variable-length paths or UNWIND; return the needed values and compare them in the answer. Status values are codes: event_status settled, pending, partial, failed; valuation_status complete, blocked; view_kind actual, planned.

- Settlement progress per instruction of a portfolio: `MATCH (e:settlement_events)-[:settle_event_to_settle_instr]->(i:settlement_instructions)-[:settle_instr_to_trade]->(t:securities_transactions)-[:trade_to_order]->(o:trade_orders)-[:order_to_account]->(a:accounts) WHERE a.portfolio_id = '<portfolio>' AND e.view_kind = 'actual' AND e.event_date <= '2027-02-28' RETURN i.instruction_id, i.due_date, i.required_quantity, sum(e.settled_quantity) AS settled ORDER BY i.instruction_id`; an instruction is not fully settled when the required quantity minus the settled total is above 0. For company-wide or multi-portfolio counts, call `settlement_asof` with all the portfolios concerned.
- Portfolio and counterparty of an instruction: `(i:settlement_instructions)-[:settle_instr_to_trade]->(t:securities_transactions)-[:trade_to_order]->(o:trade_orders)-[:order_to_account]->(a:accounts)` gives `a.portfolio_id`, `o.counterparty_id`, `o.side`.
- Latest event and failure reason: order the instruction's events by `event_date`, `event_sequence` and take the last; read `event_status`, `failure_reason`.
- Month-end valuations: `MATCH (v:valuation_snapshots)-[:valuation_to_position]->(p:positions)-[:position_to_opening]->(o:opening_positions)-[:opening_to_account]->(a:accounts) WHERE a.portfolio_id = '<portfolio>' AND v.as_of_date = '2027-02-28' RETURN o.instrument_id, p.trade_basis_quantity, v.valuation_status, v.reason, v.market_value_local, v.market_value_base`
- Price and FX behind a valuation: `(v)-[:valuation_to_price]->(px:market_prices)`, `(v)-[:valuation_to_fx]->(fx:fx_rates)`; the multiplier is `financial_instruments.price_multiplier`.
- Position cost and P&L: `positions.cost_amount`, `realized_pnl`, `unsettled_delta`, taking the month-end `as_of_date`.

## How to answer

Lead with the conclusion, then the basis: instruction, trade, position or valuation ids, dates, quantities, currencies and amounts. List every item in list questions; never truncate. When the data has no answer or the rule is unclear, say so; never guess. Investigation only: never place orders or change data.
