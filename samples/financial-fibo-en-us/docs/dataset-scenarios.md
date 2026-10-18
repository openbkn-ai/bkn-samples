# Data design and business branches

200 portfolios each have eight positions across four issuers, each issuing an equity and a bond. 100 instruments and 50 issuers are reused across portfolios; there are also 50 brokers and 50 managers. Each position has an opening and five months of staggered orders, fills, multi-event settlement, position snapshots and valuations. Prices rise and fall, producing both positive and negative realized/unrealized P&L. Every portfolio/month has four issuer exposures and one counterparty receivable. Names describe fictional businesses rather than repeated batch labels.

| Primary branch | Portfolios | Count | Current difference |
|---|---|---:|---|
| Normal settlement | PF-(001–018)+50n | 72 | Fully settled; no own primary pricing defect |
| Pending settlement | PF-(019–028)+50n | 40 | Twenty not yet due; twenty partially settled with overdue balances |
| Failed settlement | PF-(029–034)+50n | 24 | Insufficient securities / cash mismatch; open receivables retained |
| Price exception | PF-(035–040)+50n | 24 | Two stale instruments, two unapproved, two missing, with cross-portfolio propagation |
| Issuer breach | PF-(041–045)+50n | 20 | Concentrated issuer allocation; 30% threshold |
| Counterparty breach | PF-(046–048)+50n | 12 | Failed sell receivables exceed USD 500 |
| Future limit change | PF-(049–050)+50n | 8 | 80% currently; 20% from 2027-03-15 |

Here n=0,1,2,3 denotes four groups of portfolio configurations with distinct names, amounts and trade dates. Primary branches are not mutually exclusive: six defective shared instruments propagate across portfolios, including pending/failed segments. Evaluate actual evidence rather than branch labels; acceptance queries derive all impact counts. Forecast prices remain explicitly planned.

## All table sizes

| Table | Records |
|---|---:|
| `legal_entities` | 150 |
| `legal_entity_identifiers` | 150 |
| `financial_instruments` | 100 |
| `security_identifiers` | 100 |
| `portfolios` | 200 |
| `accounts` | 200 |
| `opening_positions` | 1600 |
| `trade_orders` | 8000 |
| `securities_transactions` | 8000 |
| `settlement_instructions` | 8000 |
| `settlement_events` | 16176 |
| `positions` | 8000 |
| `market_prices` | 498 |
| `fx_rates` | 150 |
| `valuation_snapshots` | 8000 |
| `issuer_exposures` | 4000 |
| `exposure_contributions` | 8000 |
| `counterparty_exposures` | 1000 |
| `mandate_limits` | 1032 |
| `limit_assessments` | 5000 |
| **Total** | **78356** |

## Acceptance allocation

Each of ten scenarios has 10 questions: 3 easy/basic, 4 intermediate, 3 hard/complex, for 100 in total:

- S01 Reference identity
- S02 Order and executed trade
- S03 Settlement investigation
- S04 Position reconciliation
- S05 Price quality
- S06 Currency conversion
- S07 Valuation and P&L
- S08 Issuer concentration
- S09 Unsettled receivables
- S10 Dates and future mandates
