# PRD: Investment Portfolio Post-Trade Control Sample

## Business context

Investment-management facts normally sit in security master, order management, custody, fund accounting, pricing, and risk systems. The hard business question is not where a trade or price is recorded, but whether a portfolio position is settled, valued with an approved price, within its mandate, and exposed to an acceptable counterparty. Manual joins make the answer slow and difficult to evidence.

This sample provides an auditable, fictitious post-trade control flow from instrument and legal-entity reference data through executed trade, settlement, position, market price, valuation, and mandate-limit assessment. It supports investigation and data interoperability; it does not execute trades, produce an official NAV, or make investment decisions.

## Stakeholders and concerns

| Stakeholder | Business concern | Required outcome |
|---|---|---|
| Portfolio manager | Is a portfolio’s exposure within the approved mandate and which position drives an exception? | Position-level exposure with the instrument, issuer, valuation date, and applicable limit. |
| Middle-office owner | Which trades remain unsettled or failed, and what positions are affected? | Trade-to-settlement evidence with an explicit status and affected position. |
| Fund accountant | Can a valuation be traced to a dated market price and currency? | Price provenance, valuation date, quantity, and calculated market value. |
| Risk and compliance owner | Do issuer concentration or unsettled counterparty sell receivables exceed their respective limits? | Aggregated exposure, limit basis, breach state, and contributing records. |
| Data and ontology owner | Are financial terms consistent across the source systems? | FIBO-anchored concepts with local operational extensions documented explicitly. |

## P0 decisions and scenarios

The sample must answer the following business decisions with supporting records, not only a boolean result:

1. Determine whether a trade is settled, pending, or failed as of a business date and identify the affected portfolio position.
2. Explain a position’s market value from quantity, instrument, price, price source, currency, and valuation date.
3. Identify positions with stale, missing, or unapproved prices and distinguish a price-data exception from a trading exception.
4. Aggregate issuer exposure and unsettled counterparty sell receivables by portfolio and compare each with its applicable mandate limit.
5. Trace an exposure breach to the positions and trades that created it, including a settlement exception where present.
6. Compare a future dated portfolio plan or limit effective date through March 2027 without presenting a future fact as current knowledge.

## Business scope

The initial vertical uses publicly tradable equity and debt instruments, fictional legal entities with clearly synthetic local entity identifiers, and fictional market prices. The connected domains are:

- **Reference data:** instruments, identifiers, issuers, legal entities, currencies, portfolios, accounts, counterparties, mandate limits, and pricing sources.
- **Post-trade operations:** orders, executed trades, settlement instructions, settlement events, and settlement status.
- **Position and valuation:** positions, dated market prices, valuation snapshots, foreign-exchange rates, issuer exposure, unsettled counterparty sell receivables, and limit assessments.

Business dates use date-only fields. The dataset spans November 2026 through March 2027. The observation date is 2027-02-28; November through February views are actual, while March is a future plan known on that date. A stated as-of date governs every position, price, exposure, and limit conclusion. Planned future limits and forecast scenarios are labelled as such and are never silently substituted for actual settled facts.

## Success criteria

Users can navigate instrument → issuer → trade → settlement → position → price → valuation → exposure → limit assessment in one connected model. Each decision exposes its date, source record, state, and failure reason. English and Chinese samples contain equivalent facts, decisions, coverage, and acceptance questions. Synthetic data is unmistakably labelled and cannot be used as a market-data or regulatory-reporting source.

## Boundary

The sample does not calculate regulatory capital, perform real-time market-risk analytics, optimize orders, determine best execution, replace an accounting ledger, or validate legal obligations. It excludes derivatives lifecycle, collateral, corporate actions, tax, client suitability, AML/KYC screening, and official NAV production. These require product-specific conventions, legal agreements, source-system controls, and governance that a self-contained sample must not imply.

## Relationship to solution design

This PRD records business outcomes and acceptance evidence. The BKN model, FIBO mapping, locked records, metrics, functions, Skills, and installation hooks are implementation choices and must not broaden this scope. Metrics, functions, or Skills will be added only when a P0 decision cannot be reproducibly answered from the installed model and documented query path.
