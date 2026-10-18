# BKN ontology specification and financial rules

## Native format and identity

Use the repository's native BKN format: YAML frontmatter plus Markdown, sole entry point `kn/network.bkn`, and separate object, relation and concept-group directories. Stable primary keys, relation IDs and filenames are retained; all IDs and names fit the 40-character platform limit. Every property maps to a CSV field. Environment-specific resource IDs are left for a future installation binding.

References: SDK `skills/create-bkn/references/SPECIFICATION.llm.md` and `openbkn bkn validate`. Native local evidence is in `verification/bkn-validation.json`.

## Financial rules

- **Views:** 2027-02-28 is the observation date. Earlier month-end snapshots are actual. March is a plan known on 2027-02-28; its trades, prices and FX are fictional forecasts.
- **Calendar:** use an explicitly fictional Monday–Friday and T+2 business-day convention, without jurisdiction holidays or real-market claims. Snapshot dates may fall on weekends; quotes/fixings come from the preceding weekday. Date plus per-instruction event sequence establishes ordering without timestamps.
- **Identity:** entities, instruments and portfolios are fictional. `DEMO-ENTITY-*` and `DEMO-SEC-*` are local identifiers, not valid LEIs, ISINs or regulatory registrations.
- **Quantity bases:** each portfolio has eight positions across four issuers, each with an equity and a bond. Trade-date quantity = opening quantity plus known signed trades executed by the snapshot date. Settlement-date quantity = opening quantity plus signed settlement-event transfers effective by that date. Their difference is the unsettled delta. The sample is long-only and cannot oversell.
- **Settlement:** one instruction per trade. `settled_quantity` is incremental, not cumulative. Instructions can contain acknowledgements, partial transfers and recoveries. Offline `settlement_state` represents current actual aggregation; `settlement_month_end` aggregates at each fill month-end. `tools/settlement_views.py` creates these evidence views, not additional BKN objects or platform functions. Filter by as-of and knowledge date, sum eligible transfers, then take the last event state. Actual views exclude planned events. Actual orders, fills and settlement events are booked on their occurrence date in this sample; completed transfers cannot be known in advance. March includes normal projected settlement, partial/failure exceptions and explicit recoveries of February instructions, not universal non-settlement. Failed/pending events transfer zero; partial events transfer a positive amount below required quantity. An instruction due after the observation date is neither overdue nor automatically failed.
- **Cost and P&L:** buys increase cost at execution price times unit factor. Before a sale, weighted-average unit cost is remaining cost divided by quantity. Realized P&L = sold quantity × (execution price × factor − pre-sale average unit cost). `realized_pnl` is the current month's local-currency realized P&L. Remaining cost is booked to two decimal places before FX conversion. Unrealized USD P&L = USD market value − remaining cost translated at current FX. Historical FX P&L, fees, taxes, coupons and corporate actions are excluded.
- **Equities and debt:** equities quote per share, factor 1. Bonds use face units and dirty price per 100 face, factor 0.01. Dirty price already includes accrued interest; no second accrued-interest adjustment or coupon cash ledger is implied.
- **Prices:** select the same instrument and `as_of_date` quote as the valuation snapshot; its `price_date` may be older. The quote must be approved, no more than 3 calendar days old and published by the snapshot date. Missing, stale and unapproved prices block valuation separately. No stale-price fallback or zero-value substitution occurs.
- **FX and rounding:** rates are USD per source-currency unit and share the valuation snapshot date. Local value = trade-date quantity × price × factor, rounded to 2dp. USD value = rounded local value × FX, again rounded to 2dp. Financial reconstruction uses Decimal / ROUND_HALF_UP; ratios and FX have 6dp. Offline SQLite queries compare frozen results with a 0.000001 tolerance; independent financial validation uses Decimal.
- **Issuer concentration:** numerator is the two contributing instrument values for that issuer; denominator is all eight USD position values for the portfolio/date. Any incomplete position blocks every issuer ratio for that portfolio. `exposure_contributions` retains valuation membership; a partial denominator cannot pass as complete.
- **Counterparty measure:** the technical table name `counterparty_exposures` means **unsettled sell receivable**. For the same portfolio/counterparty, sum remaining sell quantity × execution price × unit factor × dated FX and round to 2dp. Buy payables are excluded; no netting is applied. This is not replacement cost, PFE, EAD or regulatory CCR.
- **Limits:** issuer limits are ratios from 0 to 1; receivable limits are USD amounts. Use only an approved version valid on the assessment date and known at the observation date. A strict greater-than comparison breaches; missing observations remain unknown. Excess is `max(0, observed − threshold)` in the measure's own units.

## Object and record dictionary

| ObjectType | Name | Records | Primary key | Relationship keys |
|---|---|---:|---|---|
| `legal_entities` | Legal Entity | 150 | `entity_id` | — |
| `legal_entity_identifiers` | Entity Identifier | 150 | `identifier_id` | entity_id → legal_entities |
| `financial_instruments` | Financial Instrument | 100 | `instrument_id` | issuer_id → legal_entities |
| `security_identifiers` | Security Identifier | 100 | `identifier_id` | instrument_id → financial_instruments |
| `portfolios` | Investment Portfolio | 200 | `portfolio_id` | manager_id → legal_entities |
| `accounts` | Investment Account | 200 | `account_id` | portfolio_id → portfolios |
| `opening_positions` | Opening Position | 1600 | `opening_id` | account_id → accounts; instrument_id → financial_instruments |
| `trade_orders` | Trade Order | 8000 | `order_id` | account_id → accounts; instrument_id → financial_instruments; counterparty_id → legal_entities |
| `securities_transactions` | Executed Trade | 8000 | `trade_id` | order_id → trade_orders |
| `settlement_instructions` | Settlement Instruction | 8000 | `instruction_id` | trade_id → securities_transactions |
| `settlement_events` | Settlement Event | 16176 | `event_id` | instruction_id → settlement_instructions |
| `positions` | Dated Position | 8000 | `position_id` | opening_id → opening_positions |
| `market_prices` | Market Price | 498 | `price_id` | instrument_id → financial_instruments |
| `fx_rates` | FX Rate | 150 | `fx_id` | — |
| `valuation_snapshots` | Position Valuation | 8000 | `valuation_id` | position_id → positions; price_id → market_prices; fx_id → fx_rates |
| `issuer_exposures` | Issuer Exposure | 4000 | `exposure_id` | portfolio_id → portfolios; issuer_id → legal_entities |
| `exposure_contributions` | Exposure Contribution | 8000 | `contribution_id` | exposure_id → issuer_exposures; valuation_id → valuation_snapshots |
| `counterparty_exposures` | Unsettled Receivable | 1000 | `exposure_id` | portfolio_id → portfolios; counterparty_id → legal_entities |
| `mandate_limits` | Mandate Limit | 1032 | `limit_id` | portfolio_id → portfolios; entity_id → legal_entities |
| `limit_assessments` | Limit Assessment | 5000 | `assessment_id` | limit_id → mandate_limits; issuer_exposure_id → issuer_exposures; counterparty_exposure_id → counterparty_exposures |

## All direct relationships

Each relation maps a named FK. Empty `price_id` and the inapplicable exposure FK on an assessment create no relation.

| ID | Source | Property | Target | Property |
|---|---|---|---|---|
| `entity_id_to_entity` | legal_entity_identifiers | entity_id | legal_entities | entity_id |
| `instrument_to_issuer` | financial_instruments | issuer_id | legal_entities | entity_id |
| `security_id_to_instrument` | security_identifiers | instrument_id | financial_instruments | instrument_id |
| `portfolio_to_manager` | portfolios | manager_id | legal_entities | entity_id |
| `account_to_portfolio` | accounts | portfolio_id | portfolios | portfolio_id |
| `opening_to_account` | opening_positions | account_id | accounts | account_id |
| `opening_to_instrument` | opening_positions | instrument_id | financial_instruments | instrument_id |
| `order_to_account` | trade_orders | account_id | accounts | account_id |
| `order_to_instrument` | trade_orders | instrument_id | financial_instruments | instrument_id |
| `order_to_counterparty` | trade_orders | counterparty_id | legal_entities | entity_id |
| `trade_to_order` | securities_transactions | order_id | trade_orders | order_id |
| `settle_instr_to_trade` | settlement_instructions | trade_id | securities_transactions | trade_id |
| `settle_event_to_settle_instr` | settlement_events | instruction_id | settlement_instructions | instruction_id |
| `position_to_opening` | positions | opening_id | opening_positions | opening_id |
| `price_to_instrument` | market_prices | instrument_id | financial_instruments | instrument_id |
| `valuation_to_position` | valuation_snapshots | position_id | positions | position_id |
| `valuation_to_price` | valuation_snapshots | price_id | market_prices | price_id |
| `valuation_to_fx` | valuation_snapshots | fx_id | fx_rates | fx_id |
| `issuer_exp_to_portfolio` | issuer_exposures | portfolio_id | portfolios | portfolio_id |
| `issuer_exp_to_issuer` | issuer_exposures | issuer_id | legal_entities | entity_id |
| `contribution_to_issuer_exp` | exposure_contributions | exposure_id | issuer_exposures | exposure_id |
| `contribution_to_valuation` | exposure_contributions | valuation_id | valuation_snapshots | valuation_id |
| `cp_exp_to_portfolio` | counterparty_exposures | portfolio_id | portfolios | portfolio_id |
| `cp_exp_to_counterparty` | counterparty_exposures | counterparty_id | legal_entities | entity_id |
| `limit_to_portfolio` | mandate_limits | portfolio_id | portfolios | portfolio_id |
| `limit_to_entity` | mandate_limits | entity_id | legal_entities | entity_id |
| `assessment_to_limit` | limit_assessments | limit_id | mandate_limits | limit_id |
| `assessment_to_issuer_exposure` | limit_assessments | issuer_exposure_id | issuer_exposures | exposure_id |
| `assessment_to_counterparty_exposure` | limit_assessments | counterparty_exposure_id | counterparty_exposures | exposure_id |

## Capability choice

Dated materialized snapshots and direct relations support the local P0 acceptance. SQL is an offline test oracle, not a published function; generators do not execute at runtime. No metrics, functions or Skills are introduced. Live platform recalculation would require its own explicit contract and actual invocation acceptance.
