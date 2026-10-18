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
 'exposure_amount':('Issuer numerator: sum of contributing position USD values; unavailable when portfolio pricing is incomplete.','发行方分子为构成持仓美元市值之和；组合价格不完整则不可用。'),
 'denominator_amount':('All securities-position USD values in this portfolio/date; any blocked position makes this blank. Cash is excluded.','该组合同日全部证券持仓美元市值；任一受阻则为空，不含现金。'),
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
"""Business analysis contract (applies to every question, not precomputed answers):
- Current means the observation-date snapshot, not the sum of historical snapshots. All-actual history is a different explicitly requested scope. Select actual/planned and known_date consistently; forecast facts cannot enter actual results.
- Day-only dates may be transported as ISO midnight strings. Normalize to YYYY-MM-DD/date before local comparison. Decimal fields may arrive as strings; use Decimal(str(value)). Controlled values are localized: use the allowed values in property descriptions, never assume English statuses in a Chinese network.
- A settlement event is incremental. At cutoff, keep event_date and known_date <= cutoff, sum transfers per instruction, and take the last event ordered by (event_date,event_sequence) for state. Do not add an acknowledgement again or count history rows as instructions. Monthly contractual/receivable analysis uses each trade month's last day, knowledge <= min(observation date, month end); only future months permit planned events known at observation.
- Trade translation selects the actual USD fixing with latest as_of_date among rows whose as_of_date, published_date and known_date are <= the trade date. Translate unrounded amounts and round the grouped sum half-up to 2dp. Valuation instead follows its explicit fx_id for the snapshot. Never mix those two FX selection rules.
- Booked contract consideration gross_amount = ROUND_HALF_UP(quantity * execution_price * price_multiplier, 2) in local currency. Actual contractual-amount reports must sum this recorded amount, not reverse its per-trade booking rounding. Unrounded FX translation means gross_amount * rate before rounding the group sum. Monthly cohort open-sell notionals are instead quantity-based local amounts unless USD is explicitly requested. Equity factor is 1; per-100-face dirty bond factor is 0.01. Snapshot local market value is rounded to 2dp before FX; base value then rounds to 2dp. Current-snapshot market value is not cash, NAV or total return.
- Portfolio quantity reconciles when trade_basis - settled_basis - unsettled_delta = 0. A nonzero unsettled delta is not a reconciliation failure. Buy/sell directions and instrument units matter; never add shares and face units as a business quantity.
- A portfolio value requires every position priced completely. Missing values remain null. Issuer shares use all complete securities assets as denominator, and all its issuer exposures must sum to one. Do not assume two issuers after joining instrument pairs.
- Receivable is nonnetted open sell quantity * execution quote * multiplier * as-of USD rate. Accumulate unrounded contributions then round the total; displayed rounded lines may have a rounding residual. Use explicit limit validity/approval/known dates; unknown is not within-limit, equality does not breach.
- Follow relation source -> target as declared in mapping rules. Cypher supports joins/grouping/aggregates but not WITH, CASE, date functions or arbitrary SQL. Use run_code for cumulative/latest-event logic, conditional aggregation or Decimal arithmetic. Tool results are query_object_instance.datas or run_cypher.entries; use documented pagination and explicit limits.
- Answer the requested measure and scope only. If a question requests recorded value comparison, do not introduce unrelated accounting audits. Batch needed schema/data discovery and calculation in one run_code workflow when useful. Print a compact result, not an entire raw data dump. For full lists provide every requested row, preferably compact columns/data or grouped identifiers, with counts to prove completeness; do not duplicate the list in prose.
""",
"""通用业务分析口径（适用于全部业务问题，不含预计算答案）：
- “当前”指观察日的单个快照，不是历史快照加总；“全部实际历史”是另一种明确范围。统一 actual/planned 对应本地取值和 known_date，预测不得混入实际。
- 日期可能被接口序列化为零点 ISO 字符串，计算前先归一为 YYYY-MM-DD/date。decimal 字段可能返回字符串，使用 Decimal(str(value))。中文网络必须使用属性描述声明的中文枚举，不能假设英文状态仍可过滤。
- 结算事件为增量。按截止日同时过滤 event_date、known_date，逐指令累计转移量，按 (event_date,event_sequence) 取最后状态；确认消息不得重复算转移量，事件历史行数不等于指令数。按交易月份核对合约/应收时，结算截止为该月末，知识截止为 min(观察日,月末)；只有未来月份允许观察日已知的计划事件。
- 成交折算：从实际 USD 汇率中选择 as_of_date 最近且 as_of_date、published_date、known_date 均不晚于成交日的记录。先累加未舍入折算金额，分组后按四舍五入舍入两位。估值则沿用其明确 fx_id 对应的快照汇率，不能混用两类汇率规则。
- 入账合约金额 gross_amount=ROUND_HALF_UP(数量×成交报价×价格乘数,2)，单位为本币。实际合约金额报告应汇总该入账字段，不能撤销逐笔入账舍入。“未舍入汇率折算”指 gross_amount×汇率在分组合计前不再舍入。月度成交队列的剩余卖出名义金额按剩余数量计算，默认本币，明确要求美元时才折算。股票因子1，债券每百元面值全价因子0.01。快照本币市值先舍入两位，再乘汇率并舍入美元两位；市值不是现金、净值或总投资收益。
- 数量勾稽检查 trade_basis-settled_basis-unsettled_delta 是否为0，非零未结算差量不等于勾稽失败。需保持买卖符号和工具单位，不得把股数与面值单位混作业务数量。
- 完整组合估值要求全部持仓估值完整；未知保持NULL。发行方分母为同日完整证券资产总市值，全部发行方份额合计为1；工具两两归属发行方不表示组合只有两个发行方。
- 未结算应收为非净额未结算卖出数量×成交报价×乘数×截至日美元汇率；未舍入构成加总后舍入，展示行舍入合计可能存在尾差。限额核对需同时考虑有效期、批准与已知日期；无法判定不等于限额内，等于阈值不超限。
- 按关系映射声明的源→目标连接。Cypher可关联、分组、聚合，但不支持WITH、CASE、日期函数或任意SQL；累计/最新事件、条件聚合和Decimal计算使用run_code。query_object_instance取datas，run_cypher取entries；遵循分页并显式设置返回行数上限。
- 严格回答题目所问指标和范围，比较已记录金额时不扩张成无关会计审计。适用时在一个run_code流程内完成批量探查、取数、计算，仅打印紧凑结果，不打印整表原始数据。完整清单必须全量，可用紧凑columns/data或按组合分组的ID列表并提供行数；正文不重复整张结果表。
""")
