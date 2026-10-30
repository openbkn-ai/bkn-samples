---
name: fibo-post-trade-operations-zh-cn
description: >
  用于知识网络 financial_fibo_zh_cn 上中台运营和基金会计的问题：成交与结算指令、交收状态、
  失败与逾期、持仓数量与成本、已实现损益、价格与汇率、市值计算、估值受阻原因和月结核对。
---

# 交易后运营

回答中台和会计关于交收、持仓、估值和月结的问题。查数、汇总、追关系和读月末快照用 Cypher；问非月末日期或按更早某天当时已知的情况时调用函数。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28，“现在、今天”指这一天。十一月至二月是实际，三月是计划；计划数据不能说成已经发生。
- “某天的情况”只算日期不晚于当天、known_date 也不晚于当天的记录。
- 交收：结算事件是增量，按指令累加。合计等于应交收数量为已结算；否则最近一个事件失败为结算失败，有部分交收为部分结算，没有交收为待结算。超过应交收日仍未交收完为逾期，和失败分开说。
- 持仓：交易口径和已交收口径分别计量，unsettled_delta 是差额。成本按加权平均，已实现损益按本币，不同币种不直接相加。
- 估值：只用已批准、价格日期距估值日期不超过 3 个自然日的价格和当天唯一汇率；价格陈旧、未批准或缺失则估值受阻，不能用更早价格顶替。本币市值 = 数量 × 价格 × 计价乘数（股票 1，债券 0.01），到分；美元市值 = 本币市值 × 汇率，到分。
- 未知不等于零：组合里有估值受阻时组合总市值未知，其余证券金额可以单独给出。
- 月结：按成交月份和本币币种汇总，买入为正、卖出为负；未交收卖出名义金额（剩余数量 × 成交价 × 乘数，本币）单独列。

## 什么时候调用函数

- `settlement_asof`：问非 2 月 28 日的某天、或按更早某天当时已知的信息看交收状态、剩余数量、逾期和失败。传 `portfolio_ids`、`as_of_date`、`knowledge_date`（“当时已知”与 as_of_date 相同）、`view_kind`（实际或计划）。
- `valuation_asof`：问非月末日期的持仓、成本、损益或市值，或要从原始成交解释成本变化。
- 今天（2 月 28 日）的交收状态和月末的持仓、估值可以直接用 Cypher：月末快照与按原始记录重算的结果一致。
- 函数返回后检查 `completeness` 和 `issues`；调用失败不能当成没有记录。

## Cypher 写法

对象类型名就是标签，例如 `settlement_events`、`valuation_snapshots`。日期是 YYYY-MM-DD 字符串，可直接比较。支持关联、聚合（count、count DISTINCT、sum）和 ORDER BY。为兼容 OpenBKN 0.2.1，不用 WITH、CASE、coalesce 等函数、关系变量、返回整个节点、属性与属性比较、变长路径和 UNWIND；把需要的值查出来，在回答里比较。中文网络的状态取值是中文，例如 event_status 为“已结算、待结算、部分结算、结算失败”，valuation_status 为“完整、受阻”，view_kind 为“实际、计划”。

- 某组合各指令的交收进度：`MATCH (e:settlement_events)-[:settle_event_to_settle_instr]->(i:settlement_instructions)-[:settle_instr_to_trade]->(t:securities_transactions)-[:trade_to_order]->(o:trade_orders)-[:order_to_account]->(a:accounts) WHERE a.portfolio_id = '<组合>' AND e.view_kind = '实际' AND e.event_date <= '2027-02-28' RETURN i.instruction_id, i.due_date, i.required_quantity, sum(e.settled_quantity) AS settled ORDER BY i.instruction_id`，应交收数量减已交收合计大于 0 的就是没交收完。全公司或多个组合的统计调用 `settlement_asof`，传全部相关组合。
- 指令所属组合和对手：`(i:settlement_instructions)-[:settle_instr_to_trade]->(t:securities_transactions)-[:trade_to_order]->(o:trade_orders)-[:order_to_account]->(a:accounts)`，`a.portfolio_id`、`o.counterparty_id`、`o.side`。
- 最近事件和失败原因：对该指令的事件按 `event_date`、`event_sequence` 排序取最后一条，读 `event_status`、`failure_reason`。
- 月末估值：`MATCH (v:valuation_snapshots)-[:valuation_to_position]->(p:positions)-[:position_to_opening]->(o:opening_positions)-[:opening_to_account]->(a:accounts) WHERE a.portfolio_id = '<组合>' AND v.as_of_date = '2027-02-28' RETURN o.instrument_id, p.trade_basis_quantity, v.valuation_status, v.reason, v.market_value_local, v.market_value_base`
- 估值用到的价格和汇率：`(v)-[:valuation_to_price]->(px:market_prices)`、`(v)-[:valuation_to_fx]->(fx:fx_rates)`；证券乘数在 `financial_instruments.price_multiplier`。
- 持仓成本和损益：`positions.cost_amount`、`realized_pnl`、`unsettled_delta`，按 `as_of_date` 取月末。

## 回答方式

先给结论，再列依据：指令、成交、持仓或估值主键，日期、数量、币种和金额。清单类问题列全，不截断。数据里查不到或口径不明确时直接说明，不猜数。只做调查，不下单、不改数据。
