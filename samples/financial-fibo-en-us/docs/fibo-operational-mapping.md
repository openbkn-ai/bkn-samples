# FIBO-to-operational mapping

## Source and license

This sample derives terminology from [EDM Council FIBO](https://github.com/edmcouncil/fibo), revision `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`. FIBO’s repository is MIT licensed. The sample will retain the source IRI, source label, source definition, source repository, revision, and license reference for every direct semantic anchor. It will not redistribute FIBO as a modified standard or claim that its synthetic records are FIBO reference data.

## Mapping rules

- A direct mapping means the operational object represents the same business concept and preserves the FIBO IRI as provenance.
- A narrowed mapping uses a FIBO concept but adds a specific operational role, date, state, or local business key required to answer a P0 decision.
- An extension is a sample operational record not asserted to be a FIBO class. It has an explicit definition and relationship to its anchor.
- OWL restrictions, anonymous classes, inverses, and inferred relationships are retained as documentation only. BKN imports direct named ObjectTypes and RelationTypes with concrete dataset endpoints.

## Initial concept inventory

| BKN operational ObjectType | FIBO anchor | Mapping status | Operational interpretation |
|---|---|---|---|
| `financial_instruments` | [FinancialInstrument](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument) | Direct | Tradable instrument master with local product attributes. |
| `equity_instruments` | [EquityInstrument](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/EquityInstrument) | Direct | Equity subtype of a financial instrument. |
| `debt_instruments` | [DebtInstrument](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/DebtInstrument) | Direct | Debt subtype of a financial instrument. |
| `security_identifiers` | [SecurityIdentifier](https://spec.edmcouncil.org/fibo/ontology/SEC/Securities/SecuritiesIdentification/SecurityIdentifier) | Direct | Local identifier record, including scheme and code. |
| `legal_entities` | [LEIRegisteredEntity](https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LEIEntities/LEIRegisteredEntity) | Narrowed | Synthetic legal entities with LEI-shaped values, never real LEIs. |
| `legal_entity_identifiers` | [LegalEntityIdentifier](https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LEIEntities/LegalEntityIdentifier) | Direct | Identifier record associated with a legal entity. |
| `portfolios` | [Portfolio](https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Ownership/Portfolio) | Narrowed | Managed investment portfolio with local account and mandate references. |
| `positions` | [Position](https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Position) | Direct | Dated long or short financial exposure. |
| `securities_transactions` | [SecuritiesTransactionContract](https://spec.edmcouncil.org/fibo/ontology/FND/TransactionsExt/SecuritiesTransactions/SecuritiesTransactionContract) | Narrowed | Executed buy or sell with execution and intended settlement date. |
| `settlement_processes` | [SettlementProcess](https://spec.edmcouncil.org/fibo/ontology/FND/TransactionsExt/SecuritiesTransactions/SettlementProcess) | Narrowed | Settlement instruction and outcome for an executed transaction. |
| `market_prices` | [MarketPrice](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/InstrumentPricing/MarketPrice) | Direct | Dated, sourced market price for an instrument. |
| `valuation_methods` | [ValuationMethod](https://spec.edmcouncil.org/fibo/ontology/FND/Arrangements/Assessments/ValuationMethod) | Direct | Method used by a valuation snapshot. |
| `valuation_snapshots` | No direct class | Extension | Auditable calculation snapshot joining a position to price, FX, method, and as-of date. |
| `mandate_limits` | No direct class | Extension | Portfolio-specific business control with a measure, threshold, currency, effective period, and approved status. |
| `limit_assessments` | No direct class | Extension | Dated evaluation of a mandate limit, including breach and contributing exposure. |
| `issuer_exposures` | `Position` and issuer relation | Extension | Aggregated exposure to one issuer from position valuations. |
| `counterparty_exposures` | `SecuritiesTransactionCounterparty` | Extension | Aggregated unsettled or settled trade exposure by counterparty. |

## Required BKN relationships

The initial operational graph must provide direct relationships for `instrument → issuer`, `instrument → identifier`, `legal entity → LEI`, `portfolio → manager`, `position → portfolio`, `position → instrument`, `trade → portfolio`, `trade → instrument`, `trade → counterparty`, `settlement → trade`, `market price → instrument`, `valuation → position`, `valuation → market price`, `valuation → valuation method`, `issuer exposure → issuer`, `issuer exposure → portfolio`, `limit assessment → mandate limit`, and `limit assessment → exposure`. Each relationship will use a named foreign-key mapping and will be verified against the locked data before release.
