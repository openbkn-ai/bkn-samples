---
name: energy-delivery-settlement-zh-cn
description: >
  用于知识网络 energy_saref4ener_zh_cn 上响应值班员和结算专员的问题：执行回执、电表读数与更正、核实电量和交付比例、
  是否达标、收入与客户补偿、净额、与结算台账的差异、结算快照，以及按某天当时已知信息回看结算。
---

# 执行与结算

回答值班和结算人员关于执行、计量和结算的问题。查回执、读数、台账和结算快照用 Cypher；算核实电量、交付比例、收入和补偿时调用函数。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28；三月的事件还不能结算，已取消的事件不结算。
- “某天的情况”只算当天已知的记录；读数和基线按电表（设备）、日期、时段取最新版本，同版本内容一致的重复提交只算一次，内容冲突则算不清。
- 只有回执为完成的分配算交付；失败或客户退出计零；缺回执算不清。实际削减 = 核定基线 × 小时数 − 有效读数（不低于零）；同一设备同一时段承诺给多个事件时按承诺电量比例分摊。交付比例 = 核实电量 ÷ 承诺电量，承诺为零时为空。
- 交付比例达到最低要求（含等于）才有收入 = 核实电量 × 奖励单价；客户补偿 = 分摊电量 × 申报成本，不论是否达标都要付；收入、补偿分别保留到分，净额可为负。
- 台账取入账日期不晚于当天的最新已入账记录；同一天两笔内容冲突的入账不能核对；没有入账为空，不是零。

## 什么时候调用函数

- `settlement_assessment`：某事件的承诺电量、核实电量、交付比例、收入、补偿、净额和与台账的差额。传 `event_ids`、`as_of_date`、`knowledge_date`（问更早某天已知的情况，或某次更正之前/之后，就把它设为相应日期）。
- 回执统计、读数版本、台账记录、结算快照用 Cypher；结算快照只记录 2027-02-28，无效的不能用，有效的也要和函数结果核对：以 `as_of_date`、`knowledge_date` 都为 2027-02-28 每次传 20 个事件重算后直接比较。`event_ids` 每次最多 20 个，可以跨日期和时段；问全部已发生事件时按日期顺序每次传 20 个，三次左右算完，不要按时段逐个调用。函数返回后检查 `completeness` 和 `issues`。

## Cypher 写法

OpenBKN 0.2.1 主线支持 WITH、CASE 和聚合，不支持变长路径和 UNWIND。代码列是英文代码。

- 执行回执：`MATCH (x:execution_logs)-[:execution_to_allocation]->(a:dispatch_allocations) WHERE a.event_id = '<事件>' RETURN x.allocation_id, x.status_code, x.reason, x.revision`（按分配取最大 revision）。
- 读数：`meter_readings` 的 `meter_id`、`response_date`、`block_code`、`actual_kwh`、`quality_code`、`revision`、`known_date`。
- 台账：`MATCH (s:settlements) WHERE s.event_id = '<事件>' RETURN s.settlement_id, s.posted_date, s.revenue_cny, s.cost_cny, s.status_code`
- 结算快照：`MATCH (s:settlement_snapshots) WHERE s.event_id = '<事件>' RETURN s.delivery_ratio, s.revenue_cny, s.quality_code`

## 回答方式

先给结论（交付多少、是否达标、收入和补偿多少、能否核对），再列依据：分配、回执、读数、台账和日期。清单类问题列全。算不清时说明卡在哪条记录，不当成零。所有结论是建议，不代表已付款。
