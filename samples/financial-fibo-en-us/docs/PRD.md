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

This PRD records business outcomes and acceptance evidence. The BKN model, FIBO mapping, locked records, metrics, functions, Skills, and installation hooks are implementation choices and must not broaden this scope. Capabilities must reproduce decisions from atomic source facts when dates, transfers, prices, FX or limits change. Recorded snapshots alone do not satisfy these decisions.


## Business workflow and acceptance priority

Morning settlement triage: middle office identifies open obligations by portfolio and business date, distinguishing overdue, not yet due, partial transfer and failed status. Trace executions, instructions and each incremental transfer; later recovery or zero-quantity acknowledgement must not double count.

End-of-day accounting review: reconstruct trade and settled positions from openings and executions; explain weighted-average cost and monthly versus cumulative realized P&L. Apply dirty bond quotes per100 face units. Missing, stale or unapproved quotes cannot become zero values. Known cost may be reported while market value remains unknown.

Risk exception decisions: compute concentration from the complete portfolio denominator; one unknown valuation cannot be silently excluded. Compute non-netted open SELL receivables, without BUY offsets. Select exactly one approved mandate known by the cutoff and effective on the business day. Missing/overlapping versions and threshold breaches are distinct findings.

Planning review: compare actual facts with known March2027 plans, naming both business and knowledge dates. Future-known mandates apply only once effective; future executions, prices and recoveries cannot become current actual facts.

P0 acceptance covers both normal and adverse outcomes, including threshold equality, missing evidence, overlapping versions, hindsight exclusion and stale snapshots after source changes. Each conclusion needs source IDs, units/currency, dates, unknown reasons and reproducible values. Template repetition is not business diversity.

## Independent knowledge and month-end reconciliation

Risk and accounting must retain an issuer's independently provable market-value amount even if another issuer lacks a qualified price. The complete portfolio denominator and every concentration ratio then remain unknown; a priced-only denominator is unacceptable. A proved zero amount remains zero, but a zero portfolio denominator still leaves the ratio unknown. Missing opening evidence must never become a zero opening. If an eligible trade can be uniquely attributed to an issuer but its amount cannot be determined, block that issuer's amount and the portfolio denominator while retaining other provable issuer amounts. If its issuer cannot be determined, no issuer amount can be certified complete.

Month-end accounting must reconcile signed booked trade gross and remaining SELL notional by trade month, local currency and actual/planned view, using evidence available at the knowledge cutoff. BUY gross is positive and SELL gross negative; remaining SELL notional stays separately identified. Do not carry an earlier trade month's open amount into a later cohort, assume local amounts are USD, or mix future-known facts into an earlier observation. The same trade-month cohort can be compared across observation dates to explain transfers and recoveries without changing its membership.

Acceptance evidence distinguishes a recorded snapshot from reconstructed components. A recorded issuer exposure may remain empty under its original portfolio-wide quality policy while a reconstructed issuer amount is independently known. Report both with their scope and reason; neither an empty snapshot nor an unknown ratio erases a supported amount. Evidence must demonstrate missing opening, localized and unlocatable trade uncertainty, zero amounts, zero denominator, currency-separated cohorts and exclusion of hindsight.

## Trust requirements

English/Chinese share facts and calculation semantics with localized business expression. Public regression, isolated holdout and data perturbation are separate evidence. For this revision, report exactly one public 100-question run per language and the explicitly authorized targeted regression separately. Do not expand to repeated model rounds or claim completed holdout/perturbation campaigns. Deterministic numeric/set/null/evidence failures cannot be overridden by model grading. Separate installation/execution failures from wrong answers and retain complete denominators. Isolated AI evaluation is not human financial certification.

Multi-observation requests allow at most 20 portfolios and 12 observations including the base; scalar requests retain the 200-portfolio input bound. The guard measures the complete compact JSON serialization as UTF-8 bytes and rejects results above 3 MiB. Native platform preflight observed a 4 MiB result quota; the 3 MiB application guard leaves transport headroom. These input-count bounds do not guarantee that every maximum-size input succeeds: result size depends on records and evidence. On a limit failure reduce portfolios or observations; never truncate required rows or evidence. The original native preflight and the single public 100-question pass per language are recorded in the [validation report](../../../docs/financial-fibo-183-readiness.zh-CN.md). Input bounds are not universal runtime guarantees. The four specified post-fix tool paths passed separately; this revision remains unpublished.
