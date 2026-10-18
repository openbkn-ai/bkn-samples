# FIBO source and operational semantic mapping

Source: [official FIBO repository](https://github.com/edmcouncil/fibo), pinned revision `2d73435a4419b66b7c9f44cb9763e35fe8ac7890` (MIT).

Six original RDFs, their license and file digests are retained. Their inventories contain **171 named classes and 71 named object/data properties**, including reused and deprecated declarations. These are source inventories, not implementation or inference coverage claims. Selected anchors are checked as nondeprecated and defined. Full OWL import closure and all FIBO domains are outside the declared scenario.

| ObjectType | Source IRI | Interpretation |
|---|---|---|
| `financial_instruments` | https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument | Operational subset; the original definition and IRI are retained in the BKN Semantic Provenance section. |
| `security_identifiers` | https://spec.edmcouncil.org/fibo/ontology/SEC/Securities/SecuritiesIdentification/SecurityIdentifier | Operational subset; the original definition and IRI are retained in the BKN Semantic Provenance section. |
| `portfolios` | https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Ownership/Portfolio | Operational subset; the original definition and IRI are retained in the BKN Semantic Provenance section. |
| `positions` | https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Position | Operational subset; the original definition and IRI are retained in the BKN Semantic Provenance section. |
| `securities_transactions` | https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/SecuritiesTransaction | Operational subset; the original definition and IRI are retained in the BKN Semantic Provenance section. |
| `market_prices` | https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/InstrumentPricing/MarketPrice | Operational subset; the original definition and IRI are retained in the BKN Semantic Provenance section. |

## Explicit operational extensions

`legal_entities` is a fictional entity registry; `legal_entity_identifiers` uses local `DEMO-ENTITY-*` codes. They do not assert FIBO LEIRegisteredEntity membership or ISO 17442 LegalEntityIdentifier status. Orders, accounts, opening positions, settlement instructions/events, dated FX, valuation snapshots, contribution records, unsettled receivables, limits and assessments are scenario operational extensions.

Equity/debt are classifications on `financial_instruments.asset_class` with explicit quote basis and multiplier; no empty subtype tables are added. A portfolio is not a legal entity, a position is not an issuer, and a counterparty is an entity in a broker role.

Anonymous restrictions, external endpoints and properties without concrete business mappings do not become catch-all relations. All 29 relations have actual foreign keys and verifiable records.
