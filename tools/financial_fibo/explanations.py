"""Evidence-bearing business conclusions, not copies of the question."""
from build import FIELDS_ZH
from labels import ALIAS_ZH
RULES={
 'S01':('Identity is established by declared keys and business roles; synthetic codes are not valid regulatory identifiers.','身份按明确业务键与角色关联；合成编码不代表有效监管标识。'),
 'S02':('Execution quantity and quote factor determine contractual consideration; executed is not the same as settled.','成交数量和报价因子确定合约对价；已成交不等于已结算。'),
 'S03':('Accumulate eligible incremental transfers per instruction and take its last eligible event for state; exclude future/planned events from current actual results.','按指令累计有效增量转移量，并取最后有效事件的状态；当前实际结论排除未来或计划事件。'),
 'S04':('Trade-basis quantity is opening plus signed fills; settled quantity is opening plus signed eligible transfers. Their difference is the unsettled delta.','交易日数量为期初加有符号成交，结算日数量为期初加有符号有效转移；两者差额为未结算差量。'),
 'S05':('An unusable price blocks valuation. Missing values stay unknown and contaminate the entire portfolio denominator; a branch label cannot override this evidence.','价格不可用会阻断估值；缺失金额保持未知并使整个组合分母不可用，分支标签不能覆盖证据。'),
 'S06':('Use USD per source-currency unit available on the stated date; multiply local amount by FX. Local amounts in different currencies cannot be summed.','使用指定日期可用的每单位源币种兑美元汇率，本币金额乘汇率；不同本币金额不可直接相加。'),
 'S07':('Equities use factor 1 and dirty-priced bonds factor 0.01. USD value is rounded local value times dated FX; translated remaining cost is subtracted for unrealized P&L.','股票因子为1，债券全价因子为0.01。舍入后的本币市值乘带日期汇率得美元市值，再减折算剩余成本得未实现损益。'),
 'S08':('Issuer concentration divides complete issuer securities value by the complete portfolio securities-asset denominator, not NAV or cash. Ratios are 0–1 values.','发行方集中度以完整发行方证券市值除完整组合证券资产分母，不是净值或现金口径；比例为0–1。'),
 'S09':('Receivable exposure includes only unsettled sells at execution price, with dated FX. Settlement failure and limit breach are different decisions; no buy-payable netting or regulatory CCR is implied.','未结算应收只含按成交价及带日期汇率计量的卖出；结算失败与超限是不同判断，不抵销买入应付，也不表示监管CCR。'),
 'S10':('Use a limit only when approved, known and effective on the assessment date. March values are projected assumptions known at February end, not observed future facts.','限额必须在评估日已批准、已知且有效。三月数值是二月底已知假设下的预测，不是已观测的未来事实。'),
}
SPECIAL={
 'FIN-009':('Missing issuer roles are explicitly counted with IS NULL, avoiding SQL three-valued-logic omissions.','发行方角色为空时用IS NULL显式计入异常，避免SQL三值逻辑漏报。'),
 'FIN-019':('The fixing is the latest published curve observation available by each execution date, not the month-end fixing; USD totals permit cross-currency comparison.','每笔成交取当时已发布的最近曲线观察，而非月末汇率；折算美元后才能跨币种比较。'),
 'FIN-020':('Each fill contributes contractual amount once despite several events. Event transfers accumulate only through that trade month-end, without consuming later recovery forecasts.','每笔成交合约额只计一次；事件转移量仅累计到该成交月末，不消费之后的恢复预测。'),
 'FIN-024':('A due date after 2027-02-28 means not yet due; pending is not synonymous with failed or overdue.','约定日在2027-02-28之后表示尚未到期；待结算不等于失败或逾期。'),
 'FIN-025':('Remaining quantity is required quantity minus cumulative transfers, not minus the quantity on an arbitrary event.','剩余数量为应结算量减累计转移量，不是减任意单个事件的数量。'),
 'FIN-043':('Quote age is calendar-day difference; a ten-day-old quote fails the three-day freshness limit even if approved.','报价日龄按日历日差计算；即使已批准，十天旧价仍超过三天上限。'),
 'FIN-046':('The absent quote produces NULL price linkage and market value; zero would fabricate evidence.','报价缺失导致价格关联和市值为NULL，补零会伪造证据。'),
 'FIN-049':('Any unpriced position blocks every issuer ratio for the portfolio; unknown is not within-limit.','任一持仓缺价会阻断该组合全部发行方比例，无法判定不等于限额内。'),
 'FIN-067':('A partial portfolio sum is displayed only for investigation. It cannot be accepted as a complete valuation or a concentration denominator.','部分加总仅用于调查，不能作为完整组合估值或集中度分母。'),
 'FIN-070':('Pre-sale weighted-average unit cost = (opening cost + eligible prior buy costs)/(opening quantity + eligible prior buy quantity); multiply execution-price minus that cost by sold quantity.','卖出前加权平均成本=(期初成本+此前有效买入成本)/(期初数量+此前有效买入数量)；卖出量乘成交价与该成本之差。'),
 'FIN-080':('Valuations contribute to the issuer numerator. Opening balances are stocks, and linked current-month fills are changes; the whole stock exposure must not be attributed to those fills.','估值构成发行方分子；期初是存量，当月关联成交是变动，不能将整个存量敞口归因于这些成交。'),
 'FIN-087':('The same settlement-failure state can be within a high receivable limit but breach a lower limit; compare amount and applicable threshold.','相同结算失败状态在较高应收限额下可能不超限，在较低限额下可能超限；需比较金额与适用阈值。'),
 'FIN-088':('Accumulate transfers before computing each open sell contribution. Sum unrounded contributions then round the aggregate, and reconcile that aggregate with the assessed receivable; display-row rounding can differ.','先累计转移再算各笔卖出构成；未舍入构成先加总再舍入，与评估应收核对；显示行单独舍入可能产生尾差。'),
 'FIN-095':('Only the version effective from 2027-03-15 applies to the March plan; it must not replace the version effective in February.','三月计划适用2027-03-15起生效版本；不得用它替换二月有效版本。'),
 'FIN-099':('The same future-limit portfolio can be within its current 80% cap and breach a planned 20% cap. The projected breach is not a current breach.','同一未来限额组合在当前80%上限下可在限额内，在计划20%上限下可超限；预测超限不是当前超限。'),
 'FIN-100':('Zero invalid uses demonstrates validity/approval/knowledge alignment for these records, not that every limit assessment is within-limit.','错误使用数为零说明这些记录的有效期、批准和知识日期一致，不代表所有评估均在限额内。'),
}
def explain(qid,scenario,rows,zh):
 idx=1 if zh else 0
 if zh:
  details='；'.join(FIELDS_ZH.get(k,ALIAS_ZH.get(k,k))+'='+('未知（NULL）' if v is None else str(v)) for k,v in list(rows[0].items())[:7])
  return f'证据返回{len(rows)}条记录；首条结果：{details}。'+SPECIAL.get(qid,RULES[scenario])[idx]
 details='; '.join(k+'='+('unknown (NULL)' if v is None else str(v)) for k,v in list(rows[0].items())[:7])
 return f'Evidence returns {len(rows)} row(s). First result: {details}. '+SPECIAL.get(qid,RULES[scenario])[idx]
