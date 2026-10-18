# FIBO 到运营模型映射

## 来源与许可

本样例术语来源于 [EDM Council FIBO](https://github.com/edmcouncil/fibo)，固定修订为 `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`。FIBO 仓库采用 MIT 许可。每个直接语义锚点都会保留来源 IRI、来源标签、来源定义、来源仓库、修订和许可引用；本样例不将自己表述为 FIBO 的修改版标准，也不将合成记录表述为 FIBO 参考数据。

## 映射规则

- **直接映射：**运营对象代表相同业务概念，并保留 FIBO IRI 作为来源。
- **收窄映射：**采用 FIBO 概念，但增加回答 P0 决策所需的运营角色、日期、状态或本地业务键。
- **扩展：**样例所需但不声称是 FIBO 类的运营记录；必须具有明确本地定义和语义锚点。
- OWL 限制、匿名类、反向属性和推理关系只作为文档保留。BKN 仅导入具名 ObjectType 和在数据集中具有明确端点的直接 RelationType。

## 初始概念清单

| BKN 运营 ObjectType | FIBO 锚点 | 映射状态 | 运营解释 |
|---|---|---|---|
| `financial_instruments` | [FinancialInstrument](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument) | 直接 | 带有本地产品属性的可交易工具主数据。 |
| `equity_instruments` | [EquityInstrument](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/EquityInstrument) | 直接 | 金融工具的股票子类。 |
| `debt_instruments` | [DebtInstrument](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/DebtInstrument) | 直接 | 金融工具的债券子类。 |
| `security_identifiers` | [SecurityIdentifier](https://spec.edmcouncil.org/fibo/ontology/SEC/Securities/SecuritiesIdentification/SecurityIdentifier) | 直接 | 含标识体系和编码的本地标识记录。 |
| `legal_entities` | [LEIRegisteredEntity](https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LEIEntities/LEIRegisteredEntity) | 收窄 | 使用 LEI 形态合成值的虚构法律实体，不使用真实 LEI。 |
| `legal_entity_identifiers` | [LegalEntityIdentifier](https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LEIEntities/LegalEntityIdentifier) | 直接 | 关联到法律实体的标识记录。 |
| `portfolios` | [Portfolio](https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Ownership/Portfolio) | 收窄 | 含本地账户和授权引用的受管理投资组合。 |
| `positions` | [Position](https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Position) | 直接 | 截至某日的多头或空头金融敞口。 |
| `securities_transactions` | [SecuritiesTransactionContract](https://spec.edmcouncil.org/fibo/ontology/FND/TransactionsExt/SecuritiesTransactions/SecuritiesTransactionContract) | 收窄 | 包含成交日和预期结算日的买入或卖出交易。 |
| `settlement_processes` | [SettlementProcess](https://spec.edmcouncil.org/fibo/ontology/FND/TransactionsExt/SecuritiesTransactions/SettlementProcess) | 收窄 | 已成交交易的结算指令和结果。 |
| `market_prices` | [MarketPrice](https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/InstrumentPricing/MarketPrice) | 直接 | 有日期和来源的工具市场价格。 |
| `valuation_methods` | [ValuationMethod](https://spec.edmcouncil.org/fibo/ontology/FND/Arrangements/Assessments/ValuationMethod) | 直接 | 估值快照使用的方法。 |
| `valuation_snapshots` | 无直接类 | 扩展 | 将持仓与价格、汇率、方法和截至日期关联的可审计计算快照。 |
| `mandate_limits` | 无直接类 | 扩展 | 含口径、阈值、币种、生效期间和批准状态的组合业务控制。 |
| `limit_assessments` | 无直接类 | 扩展 | 对授权限额的带日期评估，包含违规状态和构成敞口。 |
| `issuer_exposures` | `Position` 与发行方关系 | 扩展 | 从持仓估值汇总得出的单一发行方敞口。 |
| `counterparty_exposures` | `SecuritiesTransactionCounterparty` | 扩展 | 按交易对手汇总的已结算或未结算交易敞口。 |

## 必需的 BKN 关系

初始运营图必须提供以下直接关系：`instrument → issuer`、`instrument → identifier`、`legal entity → LEI`、`portfolio → manager`、`position → portfolio`、`position → instrument`、`trade → portfolio`、`trade → instrument`、`trade → counterparty`、`settlement → trade`、`market price → instrument`、`valuation → position`、`valuation → market price`、`valuation → valuation method`、`issuer exposure → issuer`、`issuer exposure → portfolio`、`limit assessment → mandate limit` 与 `limit assessment → exposure`。每一关系必须使用具名外键映射，并在发布前以锁定数据验证。
