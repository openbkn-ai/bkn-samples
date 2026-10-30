"""Business definitions embedded in the BKN, independent of repository prose."""
OBJECTS={
 'legal_entities':('Fictional issuer, broker or investment manager in a declared business role. Identifiers are local synthetic codes, not regulatory LEIs.','虚构发行方、经纪商或资产管理人及其业务角色，标识为本地合成编码，不是监管 LEI。'),
 'legal_entity_identifiers':('Local DEMO-ENTITY identifier linking one synthetic registry record to its entity; not an ISO 17442 registration.','本地 DEMO-ENTITY 编码与虚构实体的关联，不代表 ISO 17442 登记。'),
 'financial_instruments':('Fictional equity or debt master. An issuer can issue both asset classes; currency, face/share units and quote factor govern valuation.','虚构股票或债券主数据。同一发行方可发行两类资产；币种、面值或股数单位、报价因子决定估值口径。'),
 'security_identifiers':('Local DEMO-SEC security identifier with a named synthetic scheme; not a real ISIN.','带明确合成标识体系的本地 DEMO-SEC 证券编码，不是真实 ISIN。'),
 'portfolios':('Long-only managed portfolio in USD reporting currency. Primary branch labels are test segmentation, not a substitute for risk evidence.','以美元报告的仅多头受管理组合。主分支用于测试分群，不能替代风险证据判断。'),
 'accounts':('Multi-currency securities custody account belonging to one portfolio; currency denotes reporting currency, not a restriction on instrument denomination.','归属单个组合的多币种证券托管账户；币种字段指报告币种，不限制持仓工具的计价币种。'),
 'opening_positions':('Opening inventory and local unit cost before the first transaction month. It is a stock balance, not a trade.','首个交易月之前的期初数量与本币单位成本，是存量余额而非成交交易。'),
 'trade_orders':('Accepted or projected buy/sell instruction identifying account, instrument and broker. The example permits one fill per order.','标识账户、工具及经纪商的买卖指令，可为已接受或计划状态；本样例每单一次成交。'),
 'securities_transactions':('Actual or explicitly planned fill of an order. Contractual amount uses quote factor; it is neither settled cash nor regulatory risk exposure.','订单的实际或明确计划成交。合约金额按报价因子计算，不等于已结算现金或监管风险敞口。'),
 'settlement_instructions':('Required transfer quantity and contractual due date for a fill under the fictional weekday T+2 convention.','成交在虚构工作日 T+2 示例约定下的应转移数量和约定结算日。'),
 'settlement_events':('Incremental acknowledgement, transfer, failure or recovery event. Sum eligible transfers per instruction; use the last eligible event for state. Planned rows describe projected transfers only.','增量确认、转移、失败或恢复事件。按指令累计有效转移量，最后有效事件决定状态；计划行仅表示预测转移。'),
 'positions':('Dated trade-basis and settled-basis quantities, remaining weighted-average cost and current-month local realized P&L, with actual/planned distinction.','有日期的交易日和结算日数量、剩余加权平均成本及当月本币已实现损益，区分实际与计划。'),
 'market_prices':('Synthetic sourced last-price quote assigned to a snapshot. Prior weekday quote dates preserve market-date meaning at weekend month ends.','分配到估值快照的合成来源最新成交价。月末为周末时使用此前工作日报价，保留价格日期语义。'),
 'fx_rates':('Dated synthetic USD-per-source-unit conversion curve; prior published weekday fixing is carried to a weekend snapshot, never described as a weekend transaction.','带日期的合成美元兑源币种单位转换曲线；周末快照沿用此前已发布工作日定盘，不表述为周末成交。'),
 'valuation_snapshots':('Evidence-bearing valuation from trade-basis quantity, approved current price and dated FX. Missing, stale or unapproved prices block the value instead of producing zero.','以交易日数量、合格价格和带日期汇率为证据的估值。价格缺失、陈旧或未批准时阻断金额，不补零。'),
 'issuer_exposures':('Portfolio/issuer/date market-value share of complete portfolio securities assets; cash, NAV and regulatory capital are outside the denominator. Any unpriced position blocks all issuer shares.','组合/发行方/日期的完整证券资产市值占比；分母不包含现金、净值或监管资本。任一持仓缺价阻断所有发行方占比。'),
 'exposure_contributions':('Bridge retaining each distinct position valuation contributing to an issuer numerator, including an explicit blank value when blocked.','保留构成发行方分子的各个不同持仓估值，受阻金额明确为空的桥接记录。'),
 'counterparty_exposures':('Non-netted unsettled sell receivable at contractual price translated to USD. Buy payables, PFE, EAD and replacement-cost risk are excluded.','按合约价格折算美元的非净额未结算卖出应收，不含买入应付、PFE、EAD 或替代成本风险。'),
 'mandate_limits':('Approved dated portfolio/entity control: issuer securities-asset ratio or USD unsettled-receivable cap, with knowledge and effective dates kept separate.','已批准且带日期的组合/实体控制：发行方证券资产比例或美元未结算应收上限，批准已知日与生效日分开。'),
 'limit_assessments':('Known, valid limit compared with a same-date actual or planned observation. Strictly above breaches; equality is within; incomplete observations remain unknown.','当时已知且有效的限额，与同日实际或计划观察值比较。严格大于才超限，等于在限额内，观察不全则无法判定。'),
}
FIELDS={
 'scheme':('Declared identifier scheme, not the DEMO prefix of synthetic_code. Use the complete allowed scheme value.','标识体系名称，不是 synthetic_code 的 DEMO 编码前缀；使用完整的允许体系取值。'),
 'entity_role':('Declared issuer, broker or manager role. Investment management is represented by manager, not an invented investment_manager code.','明确声明的发行方、经纪商或管理人角色；资产管理使用声明的管理人取值，不另造角色代码。'),
 'trade_status':('Operational fill state executed/planned; actual/planned instead describes view_kind. These fields are not interchangeable.','业务成交状态为已成交或计划；实际/计划属于 view_kind 视图，两字段不能互换。'),
 'side':('Source buy/sell direction uses the language-specific allowed values. Native reconstructed row.side uses stable buy/sell machine codes in both languages.','原始买卖方向使用本语言允许值；native重算行的side在两语言中均采用稳定buy/sell机器码。'),
 'trade_basis_quantity':('Opening plus signed eligible fills by the snapshot date; units follow the instrument.','截至快照日的期初加有符号有效成交，单位随工具。'),
 'settled_basis_quantity':('Opening plus signed cumulative eligible event transfers; planned transfers cannot enter an actual snapshot.','期初加有符号有效事件累计转移量；计划转移不得进入实际快照。'),
 'unsettled_delta':('Signed trade-basis minus settled-basis quantity; a negative value can represent an unsettled sell.','有符号的交易日数量减结算日数量；负值可代表未结算卖出。'),
 'cost_amount':('Remaining weighted-average cost in instrument currency, booked to 2dp at the snapshot; not original total purchases.','快照时工具本币剩余加权平均成本，入账两位小数，不是累计买入总额。'),
 'realized_pnl':('Current calendar-month realized sale P&L in instrument currency; excludes FX translation P&L, coupons, fees and taxes.','当前日历月工具本币已实现卖出损益，不含汇兑损益、票息、税费。'),
 'price_multiplier':('1 for a per-share equity quote; 0.01 for dirty bond price per 100 face units.','每股股票报价为 1；每百元面值债券全价为 0.01。'),
 'price_basis':('Per share for equity, dirty price per 100 face for debt; must agree with asset class and multiplier.','股票按每股、债券按每百元面值全价，必须与类别及乘数一致。'),
 'unit':('Share count for equity, currency face units for bonds; not bond contract lots.','股票为股数，债券为币种面值单位，不是债券手数。'),
 'gross_amount':('Booked positive contractual consideration = quantity × execution quote × price factor rounded half-up per trade to 2dp in instrument currency. Actual contractual totals and trade-date FX translation must use this recorded gross_amount, not an unrounded reconstruction.','已入账正值合约对价=成交数量×成交报价×价格因子，逐笔按四舍五入保留本币两位小数。实际合约金额合计及成交日汇率折算使用该记录的 gross_amount，不能用未舍入重算值替代。'),
 'settled_quantity':('Incremental transfer in this event, not cumulative. Pending/failed events transfer zero; sum eligible events before calculating remaining quantity.','本事件增量转移量而非累计值。待结算/失败事件为零；计算剩余量前需累计有效事件。'),
 'event_sequence':('Positive unique order within an instruction, used with event_date to order date-only events; not a timestamp.','指令内正整数唯一顺序，与事件日期共同排序，不使用时点。'),
 'event_status':('State after this event, not the whole instruction history. In planned view, settled means expected settlement, not observed completion.','本事件之后的状态，不代表整段指令历史。计划视图中已结算表示预期完成，不是已观测完成。'),
 'rate':('USD per one source-currency unit; multiply local amount by this value. USD/USD must be 1.','每单位源币种兑美元，交易币种金额乘该值；USD/USD 必须为 1。'),
 'market_value_local':('Trade-basis quantity × price × factor, rounded 2dp in instrument currency; blank if price unusable.','交易日数量×价格×因子，工具本币两位小数；价格不可用则为空。'),
 'market_value_base':('Rounded local value × same-snapshot FX, rounded 2dp USD; blank is unknown, not zero.','已舍入本币市值×同快照汇率，舍入美元两位小数；空值为未知，不是零。'),
 'cost_value_base':('Remaining booked local cost translated at current snapshot FX, 2dp USD; not historical FX cost.','剩余本币入账成本按当前快照汇率折算为美元两位小数，不是历史汇率成本。'),
 'unrealized_pnl_base':('USD market value minus USD cost translated at current FX, not total investment return or official NAV P&L.','美元市值减当前汇率折算成本，不是总投资收益或官方净值损益。'),
 'exposure_amount':('Recorded issuer numerator may be blank under snapshot-wide controls. Reconstruction preserves the issuer amount when all its contributions are known, even if another issuer blocks the portfolio denominator. Proved zero is zero; uncovered holdings cannot be zero-filled.','已记录发行方分子可能因快照全局控制留空。重算按发行方自身构成的完整性保留金额，其他发行方阻断组合分母不应抹去该金额；已证明零值保留零，覆盖缺失不能补零。'),
 'denominator_amount':('All securities-position USD values in this portfolio/date, excluding cash. Any unknown contribution makes the total unknown; a proved zero total remains zero but does not define an issuer ratio.','该组合同日全部证券持仓美元市值，不含现金；任一构成未知则总额未知，已证明零总额保持零，但不能据此定义发行方比例。'),
 'ratio':('Issuer numerator divided by complete securities-asset denominator, 0–1 ratio, 6dp; not percent points or NAV share.','发行方分子除完整证券资产分母，0–1 比例、六位小数；不是百分数数值或净值占比。'),
 'unsettled_receivable':('Sum of open sell quantity × execution quote × factor × as-of FX; USD 2dp, non-netted, no buy payables.','未结算卖出数量×成交报价×因子×截至日汇率之和，美元两位小数，非净额，不含买入应付。'),
 'contribution_amount':('USD value copied from one contributing valuation; blank preserves unavailable evidence.','单个构成估值的美元市值；为空保留不可用证据。'),
 'measure':('issuer_ratio uses a 0–1 securities-asset share; receivable_amount uses a USD amount.','issuer_ratio 为 0–1 证券资产比例；receivable_amount 为美元金额。'),
 'threshold':('Limit in its declared measure: 0–1 ratio or USD amount; strictly greater breaches, equality does not.','依衡量口径为 0–1 比例或美元金额；严格大于才超限，等于不超限。'),
 'observed_value':('Same-date observation in the limit measure; blank means no defensible decision, not zero.','与限额同日同口径的观察值；为空表示不能可靠判断，不等于零。'),
 'excess_value':('max(0, observation − threshold), in ratio units or USD according to measure; unknown stays blank.','max(0,观察值−阈值)，按口径使用比例或美元；未知保持为空。'),
 'known_date':('Date this fact/assumption was available; actual facts cannot use future knowledge, planned assumptions are known by 2027-02-28.','事实或假设可知日期；实际事实不能使用未来知识，计划假设必须于 2027-02-28 前已知。'),
 'view_kind':('actual is a synthetic observed fact; planned is an explicit forecast known at the observation date, never actual future completion.','实际为虚构已观测事实，计划为观察日已知的明确预测，不能充当实际未来完成。'),
 'as_of_date':('Business snapshot date, distinct from quote/fixing date and date of knowledge.','业务快照日期，区别于报价/定盘日期和已知日期。'),
 'published_date':('Business publication/fixing date; actual data must have been published before consumption.','业务发布或定盘日期，实际数据必须先发布后使用。'),
 'price_date':('Date of the underlying reported quote; previous weekday at weekend snapshot; age limit is three calendar days.','底层报价日期；周末快照取此前工作日，日龄上限为三日历日。'),
 'due_date':('Contractual date under this sample’s fictional T+2 weekday convention; not a legal market-specific settlement rule.','本样例虚构工作日 T+2 约定的到期日，不是特定市场法律结算规则。'),
 'opening_date':('Date of opening ledger balance before the first sample trade; not an execution date.','首笔样例交易前的期初账面余额日，不是成交日期。'),
 'decision_date':('Date the limit was approved and known, distinct from its effective interval.','限额获批准且已知的日期，区别于其生效区间。'),
 'effective_from_date':('Inclusive first valid business date of this limit version.','该限额版本有效区间的起日，含当日。'),
 'effective_to_date':('Inclusive last valid business date of this limit version.','该限额版本有效区间的止日，含当日。'),
 'branch':('Primary test segmentation only; shared-price defects or other evidence can affect several segments simultaneously.','仅为测试主分群；共享价格缺陷等证据可同时影响多个分群。'),
 'pricing_source':('Declared synthetic demo_pricing provider, not a live exchange or approved production feed.','已声明的合成模拟价格源，不是真实交易所或生产行情接口。'),
}
def field_description(table,field,zh,schema):
 index=1 if zh else 0
 if field in schema[table][2]:
  target=schema[table][2][field]
  return ('外键关联 '+target+'，空值仅允许在合同明确声明缺失/不适用时使用。') if zh else ('Foreign key to '+target+'; blank only where contract declares absent/inapplicable evidence.')
 if field in FIELDS:return FIELDS[field][index]
 if field==schema[table][0]:return '该业务记录的稳定唯一标识。' if zh else 'Stable unique identifier of this business record.'
 if field=='currency':
  if table in ('accounts',):return '账户报告币种，不限制工具交易币种。' if zh else 'Account reporting currency; does not constrain instrument denomination.'
  if table in ('valuation_snapshots','issuer_exposures','exposure_contributions','counterparty_exposures'):return '本位币 USD，金额以美元表达。' if zh else 'Base currency USD; amounts are expressed in dollars.'
  if table=='mandate_limits':return '金额限额为 USD；比例限额无币种，保持为空。' if zh else 'USD for amount limits; blank for dimensionless ratios.'
  return '工具计价币种，须与对应成交、结算指令、开仓及持仓一致。' if zh else 'Instrument denomination; must agree across trade, instruction, opening and position.'
 if field.endswith('_date'):return '该业务事件的日期；使用虚构工作日日历并区分计划与实际。' if zh else 'Date of this business event under the fictional weekday calendar; distinguish planned and actual.'
 if 'quantity' in field:return '正值业务数量，单位取关联工具的股数或面值单位。' if zh else 'Positive business quantity in the linked instrument’s share or face units.'
 if field in ('execution_price','cost_unit_price','price'):return '按关联工具报价口径表达的本币价格，须配合 price_multiplier 使用。' if zh else 'Local-currency quote in the linked instrument basis; apply price_multiplier.'
 if 'status' in field or field in ('reason','failure_reason','approval'):return '明确受控的状态或原因；缺失记录不得被推断为完成或通过。' if zh else 'Explicit controlled state/reason; absence never implies completion or acceptance.'
 if field=='name':return '用于业务展示的虚构名称，双语语义一致。' if zh else 'Human-readable fictional business name with equivalent bilingual meaning.'
 return '该对象的具名业务属性，取值需符合 model-contract.json 中的类型及受控词汇。' if zh else 'Named business attribute constrained by model-contract.json types and controlled vocabulary.'


ANALYSIS_CONTRACT=(
"""Business rules (defaults; a user's explicit condition wins):
- The business date is 2027-02-28; "now" and "today" mean this date. November to February are actual (view_kind actual); March is the plan known today (view_kind planned). Month end means the snapshot dated 2026-11-30, 12-31, 2027-01-31, 02-28 or the planned 03-31. Never present plan data as something that has happened.
- "The situation on a day" counts only records dated on or before that day whose known_date is on or before that day.
- Settlement events are incremental: sum settled_quantity per instruction. Settled when the total equals required_quantity; otherwise failed if the latest event (event_date, event_sequence) failed, partially settled if some quantity settled, pending if none. Outstanding past due_date is overdue, reported separately from failed.
- Positions carry trade-basis and settled-basis quantities; unsettled_delta is their difference. Cost is weighted average; realized P&L is in local currency.
- A valuation needs an approved price at most 3 calendar days older than the valuation date, and the single FX rate from the security currency to USD for that day. Stale, unapproved or missing prices block the valuation; no older price is substituted.
- Local market value = quantity × price × price_multiplier (1 for equities, 0.01 for bonds quoted dirty per 100 face), rounded half up to the cent; USD value = local value × FX rate, rounded to the cent.
- Unknown is not zero. One unknown valuation makes the portfolio total and every issuer concentration unknown; issuer amounts whose holdings are all valued stay confirmed.
- Issuer concentration = issuer USD value ÷ portfolio USD value of all securities, 6 decimals. Counterparty unsettled-sale receivable = Σ remaining sale quantity × execution price × multiplier × that day's FX, rounded after summing; purchases never offset it.
- The applicable limit is approved by the day, effective on it and unique; a new limit applies only from effective_from_date. Greater than the limit is a breach, equal is within; excess = observed − limit.
- Month-end reconciliation groups trades by trade month and local currency, buys positive and sells negative, with unsettled sale notional shown separately.

How to answer:
- Month-end valuations, positions, issuer exposures (with exposure_contributions), counterparty exposures and limit assessments are recorded snapshots that match recomputation from the original records; read them with Cypher.
- For a date that is not a month end, for what was known on an earlier day, or to explain a status from the original trades and events, call settlement_asof, valuation_asof or limit_assessment_asof.
- Cypher supports joins, aggregation (count, count DISTINCT, sum) and ORDER BY. To stay compatible with OpenBKN 0.2.1, do not use WITH, CASE, functions such as coalesce, relationship variables, whole-node returns, property-to-property comparisons, variable-length paths or UNWIND; return the needed values and compare them in the answer. Dates are YYYY-MM-DD strings and compare as text; numbers may arrive as strings, so use Decimal arithmetic.
""",
"""业务口径（默认规则；使用者明确提出别的条件时以使用者为准）：
- 业务日期为 2027-02-28，“现在”“今天”指这一天。十一月至二月是实际数据（view_kind 为实际），三月是今天已知的计划（view_kind 为计划）。月末指 2026-11-30、12-31、2027-01-31、02-28 及计划的 03-31 快照。计划数据不能说成已经发生。
- “某天的情况”只算日期不晚于当天、且 known_date 不晚于当天的记录。
- 结算事件是增量，按指令累加 settled_quantity。合计等于 required_quantity 为已结算；否则最近事件（event_date、event_sequence）失败为结算失败，有部分交收为部分结算，没有交收为待结算。超过 due_date 仍未交收完为逾期，与失败分开说明。
- 持仓有交易口径和已交收口径数量，unsettled_delta 是两者之差。成本按加权平均法；已实现损益按本币。
- 估值只用已批准、价格日期距估值日期不超过 3 个自然日的价格，以及当天证券币种兑美元的唯一汇率。价格陈旧、未批准或缺失则估值受阻，不能拿更早的价格顶替。
- 本币市值 = 数量 × 价格 × price_multiplier（股票为 1，债券按每百元面值全价为 0.01），四舍五入到分；美元市值 = 本币市值 × 汇率，再到分。
- 未知不等于零。组合里只要有一条估值未知，组合总市值和各发行方集中度都未知；持仓都已估值的发行方金额仍可确认。
- 发行方集中度 = 发行方美元市值 ÷ 组合全部证券美元市值，保留 6 位小数。交易对手未结算卖出应收 = Σ 未交收卖出剩余数量 × 成交价 × 乘数 × 当天汇率，先求和再到分；同一对手的买入不能抵减。
- 适用限额须在当天已批准、处于有效期内且唯一；新限额从 effective_from_date 起才使用。大于限额为超限，等于不超限；超出部分 = 观察值 − 限额。
- 月结按成交月份和本币币种汇总，买入为正、卖出为负，未交收卖出名义金额单独列示。

回答方式：
- 月末的估值、持仓、发行方敞口（及 exposure_contributions 构成）、交易对手敞口和限额评估是已记录快照，与按原始记录重算的结果一致，用 Cypher 直接读取。
- 问非月末日期、问更早某天当时已知的情况，或要从原始成交和交收事件解释状态时，调用 settlement_asof、valuation_asof 或 limit_assessment_asof。
- Cypher 支持关联、聚合（count、count DISTINCT、sum）和 ORDER BY。为兼容 OpenBKN 0.2.1，不用 WITH、CASE、coalesce 等函数、关系变量、返回整个节点、属性与属性比较、变长路径和 UNWIND；把需要的值查出来，在回答里比较。日期是 YYYY-MM-DD 字符串，可直接比较；数值可能以字符串返回，按 Decimal 计算。中文网络的状态等取值使用属性描述里的中文枚举。
""")
