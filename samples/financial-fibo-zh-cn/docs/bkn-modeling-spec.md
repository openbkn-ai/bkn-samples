# BKN 本体规范与财务计算口径

## 原生格式与身份

遵循仓库所用原生 BKN 规范：YAML frontmatter 加 Markdown；唯一入口 `kn/network.bkn`；对象、关系、概念分组分别位于对应子目录。结构标题、字段名保持解析器要求，业务显示名中文。对象主键和关系文件名稳定，`id/name` 均不超过 40 字符。对象全部映射本地 CSV 字段；数据源 ID 由将来的平台安装绑定，不在样例中伪造。

规范依据：SDK `skills/create-bkn/references/SPECIFICATION.llm.md` 与 `openbkn bkn validate`。本地原生验证结果保存在 `verification/bkn-validation.json`。

## 统一财务规则

- **视图：**2027-02-28 为当前观察日；此前月末为实际视图，三月为计划。计划于 2027-02-28 已知，计划成交、价格和汇率均非真实未来市场数据。
- **日历：**使用明确虚构的周一至周五工作日及 T+2 工作日示例约定，不模拟地区节假日，不声称适用于真实市场。月末快照可落周末，但价格和汇率定盘来自此前工作日；事件日期与指令内顺序共同确定先后，不使用时点。
- **身份：**法律实体、股票/债券和组合均虚构。`DEMO-ENTITY-*`、`DEMO-SEC-*` 是本地标识，不声称是有效 LEI、ISIN 或监管登记。
- **数量口径：**每组合八项持仓、四家发行方，每家同时发行股票和债券。期初数量来自 `opening_positions`；成交正负由买卖方向决定。交易日持仓 = 期初 + 已知且成交日在截至日前的有符号成交；结算日持仓 = 期初 + 事件日在截至日前的有符号实际结算量。两者差额 = 未结算差量。只允许多头，卖出量不得超过持仓。
- **结算：**每笔成交对应一张指令。事件表的 `settled_quantity` 是本次转移量，不是累计量；每张指令可含确认、部分转移和恢复等多条事件，必须按截至日和已知日先筛选，再按指令累计数量和选取最后状态。离线 `settlement_state` 表达当前实际聚合，`settlement_month_end` 表达各成交月末聚合；它们由 `tools/settlement_views.py` 创建，不是额外 BKN 对象或平台函数。实际视图排除计划事件。本样例的实际订单、成交和结算事件按发生日入账，不能提前知道已完成转移。三月正常交易按预期结算，保留部分/失败例外；二月未结算按明确恢复假设处理，不能一律当成永不结算。状态为失败或待结算时转移量为零，部分结算时大于零且小于应结算量。约定日在观察日之后的待结算不等于失败，也不算已逾期。
- **成本与损益：**买入按成交价与单位乘数增加成本；卖出前以剩余成本/剩余数量得到加权平均单位成本。已实现损益 = 卖出数量 ×（成交价 × 单位乘数 − 卖出前平均单位成本）。`realized_pnl` 是本月交易币种已实现损益。成本先按两位小数入账，再按当前汇率折算；未实现损益 = 当前美元市值 − 当前汇率折算的剩余成本。它不包含历史汇兑损益、税费、票息或公司行动。
- **股票与债券：**股票价格按每股，乘数 1；债券数量为面值单位，使用每百元面值全价，乘数 0.01。债券全价已包含应计利息，不重复加息，也不做票息现金流核算。
- **价格质量：**每个估值快照选用相同工具、相同 `as_of_date` 的报价记录，`price_date` 可早于快照。需已批准，价格年龄不超过 3 个日历日，发布日期不得晚于快照。缺失记录、陈旧报价和未批准报价分别处理，不自动回退旧价或将缺失补零。
- **汇率与舍入：**汇率方向是每一单位源币种兑 USD；估值与汇率快照日期一致。交易币种市值 = 交易日数量 × 价格 × 单位乘数，先四舍五入到两位；美元市值 = 上述已舍入市值 × 汇率，再舍入两位。金额使用 Decimal / ROUND_HALF_UP，比例与汇率保留六位。离线 SQL 采用 SQLite 数值类型，按题目指定 0.000001 容差与锁定结果比较；独立财务重算使用 Decimal。
- **发行方集中度：**分子为该组合对某发行方的两项持仓美元市值；分母为同一日期全部八项持仓美元市值。任一持仓估值受阻，该组合所有发行方集中度均无法判定。`exposure_contributions` 记录估值构成，禁止只汇总有价格部分并标记完整。
- **交易对手口径：**`counterparty_exposures` 的兼容技术名称指**未结算卖出应收金额**。按相同组合和交易对手，将截至日尚未结算的卖出数量 × 成交价 × 单位乘数 × 当前汇率求和，再舍入两位。买入应付不进入该金额，不净额抵销，不表示替代成本、PFE、EAD 或监管 CCR。
- **限额：**发行方限额以 0–1 比例表达；交易对手限额以 USD 金额表达。只有在评估日有效、当时已知且已批准的版本可用。观察值严格大于阈值才超限；未知观察值仍为无法判定。超限值为 `max(0,观察值−阈值)`，比例与金额不可混用。

## 对象与记录字典

| ObjectType | 名称 | 记录数 | 主键 | 关系外键 |
|---|---|---:|---|---|
| `legal_entities` | 法律实体 | 150 | `entity_id` | — |
| `legal_entity_identifiers` | 法律实体标识 | 150 | `identifier_id` | entity_id → legal_entities |
| `financial_instruments` | 金融工具 | 100 | `instrument_id` | issuer_id → legal_entities |
| `security_identifiers` | 证券标识 | 100 | `identifier_id` | instrument_id → financial_instruments |
| `portfolios` | 投资组合 | 200 | `portfolio_id` | manager_id → legal_entities |
| `accounts` | 投资账户 | 200 | `account_id` | portfolio_id → portfolios |
| `opening_positions` | 期初持仓 | 1600 | `opening_id` | account_id → accounts; instrument_id → financial_instruments |
| `trade_orders` | 交易订单 | 8000 | `order_id` | account_id → accounts; instrument_id → financial_instruments; counterparty_id → legal_entities |
| `securities_transactions` | 证券成交 | 8000 | `trade_id` | order_id → trade_orders |
| `settlement_instructions` | 结算指令 | 8000 | `instruction_id` | trade_id → securities_transactions |
| `settlement_events` | 结算事件 | 16176 | `event_id` | instruction_id → settlement_instructions |
| `positions` | 日期持仓 | 8000 | `position_id` | opening_id → opening_positions |
| `market_prices` | 市场价格 | 498 | `price_id` | instrument_id → financial_instruments |
| `fx_rates` | 汇率 | 150 | `fx_id` | — |
| `valuation_snapshots` | 持仓估值 | 8000 | `valuation_id` | position_id → positions; price_id → market_prices; fx_id → fx_rates |
| `issuer_exposures` | 发行方敞口 | 4000 | `exposure_id` | portfolio_id → portfolios; issuer_id → legal_entities |
| `exposure_contributions` | 敞口构成 | 8000 | `contribution_id` | exposure_id → issuer_exposures; valuation_id → valuation_snapshots |
| `counterparty_exposures` | 未结算应收金额 | 1000 | `exposure_id` | portfolio_id → portfolios; counterparty_id → legal_entities |
| `mandate_limits` | 授权限额 | 1032 | `limit_id` | portfolio_id → portfolios; entity_id → legal_entities |
| `limit_assessments` | 限额评估 | 5000 | `assessment_id` | limit_id → mandate_limits; issuer_exposure_id → issuer_exposures; counterparty_exposure_id → counterparty_exposures |

## 全部直接关系

每条关系对应具名外键。空的 `price_id` 或评估中的另一种敞口外键表示缺失或不适用，不生成空端点关系。

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

## 场景能力选择

已物化的带日期业务快照和直接关系支持本地 P0 验证。SQL 只用于验收，不作为平台函数发布；生成器不在运行期执行。暂不引入指标、函数或 Skill。未来若需要平台实时重算，必须单独定义能力契约并做真实调用验收，不能把本次离线结果当作能力已安装。
