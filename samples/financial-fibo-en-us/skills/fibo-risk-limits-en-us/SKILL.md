---
name: fibo-risk-limits-en-us
description: >
  Use for risk, compliance and portfolio-manager questions on knowledge network financial_fibo_en_us:
  issuer concentration, counterparty unsettled-sale receivables, applicable limits and breaches, why a
  limit cannot be judged, the holdings or trades behind a breach, limits about to take effect, March
  plan vs February actual, and portfolio market value.
---

# Risk and limits

Answer risk and portfolio-manager questions about concentration, counterparty receivables, limits and the plan. Use Cypher to read month-end exposures and limit assessments and to trace their contributions; call a function for a date that is not a month end or for what was known on an earlier day.

## Default rules

Unless the user says otherwise, answer with these rules and name the rule you used in one short phrase.

- The business date is 2027-02-28. November to February are actual; March is the plan known today. Use plan data only when asked about the plan, and say it is the plan.
- "The situation on a day" counts only records whose date and known_date are on or before that day.
- Issuer concentration = issuer USD value ÷ USD value of all securities in the portfolio, 6 decimals. With a blocked valuation in the portfolio, concentration cannot be judged and the denominator must not be built from the complete part only; issuer amounts whose holdings are all valued can still be confirmed.
- Counterparty unsettled-sale receivable = Σ remaining sale quantity × execution price × multiplier × that day's FX rate (USD), summed and then rounded to the cent; purchases from the same counterparty never offset it.
- Applicable limit: approved by the day, effective on it and unique; a new limit applies only from its effective date, and the old limit applies until then. Greater than the limit is a breach, equal is within; excess = observed value − limit.
- A portfolio total market value needs a value for every security; with a blocked valuation the total is unknown.

## When to call a function

- `limit_assessment_asof`: concentration, counterparty receivables and breaches for a date that is not a month end, or based on what was known on an earlier day. Pass `portfolio_ids`, `as_of_date`, `knowledge_date` and `view_kind` (actual or planned).
- `settlement_asof`: explaining which sales made up a counterparty receivable on a given day.
- Month-end (including the March plan) exposures, limit assessments and valuations can be read with Cypher: they match recomputation from the original records.
- After a function returns, check `completeness` and `issues`; a failed call never means within the limit.

## Cypher patterns

Object type names are the labels. Dates are YYYY-MM-DD strings. Joins, aggregation (count, count DISTINCT, sum) and ORDER BY are supported. To stay compatible with OpenBKN 0.2.1, do not use WITH, CASE, functions such as coalesce, relationship variables, whole-node returns, property-to-property comparisons, variable-length paths or UNWIND; return the needed values and compare them in the answer. Values are codes: assessment_status within, breach, unknown; measure issuer_ratio, receivable_amount; view_kind actual, planned.

- Limit assessments: `MATCH (a:limit_assessments)-[:assessment_to_limit]->(l:mandate_limits) WHERE a.as_of_date = '2027-02-28' RETURN l.portfolio_id, l.entity_id, l.measure, l.threshold, a.observed_value, a.assessment_status, a.excess_value`
- Issuer exposure: `issuer_exposures` with `exposure_amount`, `denominator_amount`, `ratio`, `exposure_status`; contributions: `MATCH (c:exposure_contributions)-[:contribution_to_issuer_exp]->(x:issuer_exposures), (c)-[:contribution_to_valuation]->(v:valuation_snapshots)-[:valuation_to_position]->(p:positions)-[:position_to_opening]->(o:opening_positions) WHERE x.exposure_id = '<exposure>' RETURN o.instrument_id, c.contribution_amount`
- Counterparty receivable: `counterparty_exposures.unsettled_receivable` by `portfolio_id`, `counterparty_id`, `as_of_date`.
- Limit versions: `mandate_limits` with `effective_from_date`, `effective_to_date`, `approval`, `decision_date`; limits taking effect later have `effective_from_date` after today.
- Blocked valuations: `valuation_snapshots.valuation_status`, `reason`; a security's issuer is `financial_instruments.issuer_id`.

## How to answer

Lead with the conclusion (breach or not, by how much, whether it can be judged), then the basis: limit id and threshold, observed value, date, contributing holdings or trades. List every item in list questions. Say whether figures are actual or plan. When the data has no answer, say so; never guess. Investigation only: never place orders, change data or give investment advice.
