# Portfolio Post-Trade Controls: Settlement, Valuation and Limits PRD

## Goals and users

A long-only asset manager holds equities and bonds across many portfolios. Security master data, trades, custody settlement, pricing and risk limits live in separate systems. Business users want to ask in plain business language which trades have not settled, whether a valuation can be trusted, whether an exposure is beyond its mandate and whether the plan will cause problems, and see the records and dates behind every conclusion.

| User | Concern | Expected conclusion |
|---|---|---|
| Middle office | Which trades are unsettled, failed or overdue, and which holdings they affect | instruction status, remaining quantity, due date, failure reason, affected holdings |
| Fund accountant | Whether a valuation traces to an eligible price and FX rate, and how cost and P&L arise | quantity, price, FX, local and USD market value, cost and realized P&L, blocking reason |
| Risk and compliance | Whether issuer concentration or counterparty unsettled-sale receivables exceed the mandate | exposure, applicable limit, excess, contributing holdings or trades |
| Portfolio manager | Portfolio size, and whether the plan month brings new breaches | portfolio market value, actual vs plan, limits about to take effect |

Success means users get conclusions that follow the business rules below without stating any calculation rule, together with the trades, settlements, prices, valuations and limits behind them. An answer that is only right when the rule is spelled out in the question, and wrong when it is phrased differently, does not count.

## Decision scope

In scope: instrument and issuer master data, portfolios and accounts, orders and trades, settlement instructions with incremental settlement events, month-end positions, market prices and FX rates, valuation snapshots, issuer exposures and their contributions, counterparty unsettled-sale receivables, mandate limits and limit assessments.

Out of scope: placing orders, settling or changing any record; official NAV, regulatory capital, market risk, best execution, tax, corporate actions, derivatives and collateral. Every conclusion is for investigation and decision support only.

## Business rules

These are the default rules; users do not need to repeat them. When a user states a different condition, the user's condition wins.

1. **Business date**: 2027-02-28. "Now" and "today" mean this date. November to February are actual facts; March is the plan known today. Month end means the snapshot dated the last day of the month (2026-11-30, 12-31, 2027-01-31, 02-28 and the planned 03-31).
2. **As of a day**: "the situation on a day" counts only facts that happened on or before that day and were already known that day; unless stated otherwise both are the business date. Plan data is used only for questions about the plan and is never presented as something that has happened.
3. **Settlement status**: settlement events carry incremental quantities that add up. An instruction whose settled total equals the required quantity is settled; otherwise it is failed if its latest event failed, partially settled if some quantity settled, and pending if nothing has settled. An instruction with quantity outstanding past its due date is overdue; overdue and failed are reported separately.
4. **Positions and cost**: positions are measured on a trade-date basis and a settled basis; the difference is the quantity not yet settled. Cost follows the weighted-average method, and sales realize P&L. Realized P&L is in local currency, with the month and the cumulative figures kept apart.
5. **Prices and FX**: a valuation uses only a price that applies on the valuation date, is approved, and is at most 3 calendar days older than the valuation date. A stale, unapproved or missing price cannot value a holding, and an older price must not be substituted. The FX rate is the single rate from the security's currency to USD for that day.
6. **Market value**: local market value = quantity × price × price multiplier (1 for equities; bonds are quoted dirty per 100 face, multiplier 0.01), rounded half up to the cent; USD market value = local market value × FX rate, rounded to the cent.
7. **Unknown is not zero**: a holding without a usable price has an unknown market value, never zero. If any security in a portfolio is unknown, the portfolio total is unknown; the other securities' amounts can still be stated on their own.
8. **Issuer concentration**: issuer USD market value ÷ USD market value of all securities in the portfolio, to 6 decimals. When the portfolio has an unknown valuation, concentration cannot be judged, and the denominator must not be built from the complete part only; issuer amounts whose holdings are all valued can still be confirmed.
9. **Counterparty unsettled-sale receivable**: for all sales to a counterparty not yet fully settled, remaining quantity × execution price × price multiplier × that day's FX rate in USD, summed and then rounded to the cent; purchases from the same counterparty never offset it.
10. **Limits**: matched by portfolio, issuer or counterparty, and measure. The applicable limit must be approved by that day, in its effective period, and unique; a new limit is used only from its effective date. An observed value greater than the limit is a breach; equal is within. Excess = observed value − limit.
11. **Month-end reconciliation**: totals by trade month and local currency, with buys positive and sells negative; the notional of sales not yet fully settled (remaining quantity × execution price × multiplier, in local currency) is shown separately, and trades are never carried from one month into the next.

## Business scenarios

| Scenario | User question | Expected conclusion |
|---|---|---|
| S01 Reference data and portfolios | How many portfolios, who runs them, what they hold | portfolios and managers, issuers and maturities, holdings |
| S02 Trades and settlement | Which trades are unsettled, failed or overdue | open instructions, failure reasons, overdue vs not due, affected portfolios and counterparties |
| S03 Prices and valuation | Can a valuation be trusted, how is market value derived | eligible and ineligible prices, market value calculation, blocked valuations, portfolio value |
| S04 Positions, cost and month end | How cost and P&L move, how month end reconciles | cost change and cause, realized P&L, trade vs settled difference, month end by currency |
| S05 Issuer concentration | Is an issuer limit exceeded, what makes it up | concentration, applicable limit, excess, contributing holdings, why it cannot be judged |
| S06 Counterparty receivables | What a counterparty owes us, is it over the limit | unsettled-sale receivable, contributing trades, limit and excess |
| S07 Limits and plan | Will the plan month bring new breaches | limits about to take effect, actual vs plan, planned value |
| S08 Look-back and trace | What was seen on a day, which records an exception traces to | status and amounts known on that day, trace from exception to holdings, trades and issuers |

## Acceptance

1. 50 questions per language covering the 8 scenarios: 12 basic, 20 medium, 18 complex. All asked in the business language of middle office, accounting, risk or the portfolio manager, with no calculation rule in the question.
2. Complex questions involve at least two business rules, or reasoning across three or more record types.
3. Reference answers are computed independently of the capability under test, and the tested agent never sees them.
4. One round per language, with a 100% accuracy target.
