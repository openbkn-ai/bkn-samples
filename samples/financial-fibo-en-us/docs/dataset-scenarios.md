# Dataset scenarios and acceptance coverage

## Dataset contract

The operational dataset has 50 connected fictional portfolio cases. Each core table has at least 50 records. Stable `FIN-001` through `FIN-050` business keys connect the instrument, issuer, portfolio, trade, settlement, position, market price, valuation, issuer exposure, counterparty exposure, mandate limit, and limit assessment for a case. Reference tables may contain shared records only where sharing is the business point being tested; no table is populated with a token one or two records.

All dates are dates, not timestamps. Actual activity runs from 2026-11-02 through 2027-03-31. A future-plan branch uses effective dates through 2027-03-31 and is labelled as planned. The default operational as-of date is 2027-03-31.

## Business branches

| Branch | Cases | State | Required evidence |
|---|---:|---|---|
| Settled and within limit | 18 | Trade settled; current approved price; valuation complete; issuer and counterparty exposure within limit | Positive end-to-end control path. |
| Pending settlement | 10 | Trade executed; settlement pending as of date; position has an unsettled component | Distinguish expected settlement from failure and show affected position. |
| Failed settlement | 6 | Settlement failed for a named reason; counterparty exposure remains open | Failure reason, trade, counterparty and position all remain visible. |
| Stale or missing price | 6 | Position exists but price is stale, missing, or unapproved | Valuation data-quality exception is not mislabelled as a trading exception. |
| Issuer concentration breach | 5 | Dated issuer exposure exceeds the approved portfolio limit | Limit, valuation contributors and excess amount are traceable. |
| Counterparty concentration breach | 3 | Open settlement exposure exceeds the approved counterparty limit | Pending/failed settlements feed the exposure and breach. |
| Future limit change | 2 | Limit change is approved but effective after the default as-of date | Current and future result are explicitly separated. |

These branches total 50 and deliberately include positive, pending, failed, missing-data, breach, and future-effective states. A position may be complete operationally while an independently recorded price exception prevents its valuation from being accepted.

## Evaluation design

The bilingual bank contains 100 fact-aligned questions: 30 easy/basic questions and 30 hard/complex questions, with 40 intermediate questions between them. Each English question has exactly one Chinese counterpart and the same expected evidence keys.

| Level | Count | What it proves |
|---|---:|---|
| Easy/basic | 30 | Locate an entity, instrument, trade, settlement state, price date, or limit value. |
| Intermediate | 40 | Follow two to four explicit relationships and distinguish dates, status, and source. |
| Hard/complex | 30 | Reconstruct a settlement, valuation, or exposure conclusion; aggregate contributors; compare current and future effective limits; explain exceptions. |

The test suite must include all seven branches and require an evidence-bearing answer. A correct answer cannot substitute a current price for a stale price, a planned future limit for a current limit, or an issuer exposure for counterparty exposure.
