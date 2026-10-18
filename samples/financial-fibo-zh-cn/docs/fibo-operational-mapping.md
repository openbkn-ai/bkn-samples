# FIBO 来源与运营语义映射

来源为 [FIBO 官方仓库](https://github.com/edmcouncil/fibo)，固定修订 `2d73435a4419b66b7c9f44cb9763e35fe8ac7890` (MIT).

六份原始 RDF、原始许可和摘要均随包保留。来源文件中共识别出 **171 个具名类、71 个具名对象/数据属性**；这些包含复用和废弃声明，只构成来源清单，不能据此声称已实现这些类或 OWL 推理。选用锚点均验证为非废弃且有定义。完整 OWL 导入闭包及 FIBO 全域不在本场景覆盖声明内。

| ObjectType | 来源 IRI | 映射说明 |
|---|---|---|
| `financial_instruments` | https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument | 运营子集；原始英文定义与 IRI 保存在对应 BKN 的 Semantic Provenance。 |
| `security_identifiers` | https://spec.edmcouncil.org/fibo/ontology/SEC/Securities/SecuritiesIdentification/SecurityIdentifier | 运营子集；原始英文定义与 IRI 保存在对应 BKN 的 Semantic Provenance。 |
| `portfolios` | https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Ownership/Portfolio | 运营子集；原始英文定义与 IRI 保存在对应 BKN 的 Semantic Provenance。 |
| `positions` | https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Position | 运营子集；原始英文定义与 IRI 保存在对应 BKN 的 Semantic Provenance。 |
| `securities_transactions` | https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/SecuritiesTransaction | 运营子集；原始英文定义与 IRI 保存在对应 BKN 的 Semantic Provenance。 |
| `market_prices` | https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/InstrumentPricing/MarketPrice | 运营子集；原始英文定义与 IRI 保存在对应 BKN 的 Semantic Provenance。 |

## 明确的运营扩展

`legal_entities` 是虚构实体登记表，`legal_entity_identifiers` 使用 `DEMO-ENTITY-*` 本地编码；它们不声称是 FIBO LEIRegisteredEntity 或 ISO 17442 LegalEntityIdentifier 实例。订单、账户、期初持仓、结算指令/事件、汇率观测、估值快照、敞口构成、未结算应收、授权限额及评估是本场景运营扩展。

股票和债券通过 `financial_instruments.asset_class` 分类，其报价单位和乘数明确记录；没有额外建立没有独立业务数据的子类表。组合不是法律实体，持仓不是发行方，交易对手作为法律实体的经纪商角色，而非用机构名称推断风险。

不把匿名限制、外部端点或没有业务映射的 OWL 属性转成兜底关系。29 条关系全部有实际外键，指向可验证的样例记录。
