---
name: fibo-risk-limits-zh-cn
description: >
  用于知识网络 financial_fibo_zh_cn 上风控合规和投资组合经理的问题：发行方集中度、交易对手未结算卖出应收、
  适用限额与超限、无法判定的原因、超限的构成持仓或交易、即将生效的限额、三月计划与二月实际的对比和组合市值。
---

# 风控与限额

回答风控和组合经理关于集中度、对手应收、限额和计划的问题。读月末敞口和限额评估、追溯构成用 Cypher；问非月末日期或按更早某天当时已知的情况时调用函数。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28。十一月至二月是实际，三月是今天已知的计划；问计划时才用计划数据，并说明是计划。
- “某天的情况”只算日期和 known_date 都不晚于当天的记录。
- 发行方集中度 = 发行方美元市值 ÷ 组合全部证券美元市值，保留 6 位小数。组合有估值受阻时集中度无法判定，不能只用估值完整的部分当分母；持仓都已估值的发行方金额仍可确认。
- 交易对手未结算卖出应收 = Σ 未交收卖出剩余数量 × 成交价 × 计价乘数 × 当天汇率（美元），先求和再到分；同一对手的买入不能抵减。
- 适用限额：当天已批准、处于有效期内且唯一；新限额从生效日起才用，之前仍用原限额。大于限额为超限，等于不超限；超出部分 = 观察值 − 限额。
- 组合总市值要求每只证券都有市值；有受阻估值时总市值未知。

## 什么时候调用函数

- `limit_assessment_asof`：问非月末日期、或按更早某天当时已知的信息重算集中度、对手应收和超限。传 `portfolio_ids`、`as_of_date`、`knowledge_date`、`view_kind`（实际或计划）。
- `settlement_asof`：要按某天当时的交收情况解释对手应收由哪些卖出构成。
- 月末（含三月计划）的敞口、限额评估和估值直接用 Cypher：它们与按原始记录重算的结果一致。
- 函数返回后检查 `completeness` 和 `issues`；调用失败不能当成限额内。

## Cypher 写法

对象类型名就是标签。日期是 YYYY-MM-DD 字符串。支持关联、聚合（count、count DISTINCT、sum）和 ORDER BY。为兼容 OpenBKN 0.2.1，不用 WITH、CASE、coalesce 等函数、关系变量、返回整个节点、属性与属性比较、变长路径和 UNWIND；把需要的值查出来，在回答里比较。中文网络的取值是中文：assessment_status 为“限额内、超限、无法判定”，measure 为“发行方集中度、未结算应收金额”，view_kind 为“实际、计划”。

- 限额评估：`MATCH (a:limit_assessments)-[:assessment_to_limit]->(l:mandate_limits) WHERE a.as_of_date = '2027-02-28' RETURN l.portfolio_id, l.entity_id, l.measure, l.threshold, a.observed_value, a.assessment_status, a.excess_value`
- 发行方敞口：`issuer_exposures` 的 `exposure_amount`、`denominator_amount`、`ratio`、`exposure_status`；构成：`MATCH (c:exposure_contributions)-[:contribution_to_issuer_exp]->(x:issuer_exposures), (c)-[:contribution_to_valuation]->(v:valuation_snapshots)-[:valuation_to_position]->(p:positions)-[:position_to_opening]->(o:opening_positions) WHERE x.exposure_id = '<敞口>' RETURN o.instrument_id, c.contribution_amount`
- 对手应收：`counterparty_exposures` 的 `unsettled_receivable`，按 `portfolio_id`、`counterparty_id`、`as_of_date`。
- 限额版本：`mandate_limits` 的 `effective_from_date`、`effective_to_date`、`approval`、`decision_date`；未来生效的限额 `effective_from_date` 晚于今天。
- 估值受阻：`valuation_snapshots` 的 `valuation_status`、`reason`；证券发行方在 `financial_instruments.issuer_id`。

## 回答方式

先给结论（是否超限、超多少、能否判定），再列依据：限额主键与阈值、观察值、日期、构成持仓或交易。清单类问题列全。说明实际还是计划。数据里查不到时直接说明，不猜数。只做调查，不下单、不改数据，不给投资建议。
