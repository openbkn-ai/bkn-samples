---
name: energy-capacity-dispatch-zh-cn
description: >
  用于知识网络 energy_saref4ener_zh_cn 上聚合商运营负责人和企业能源经理的问题：客户、场所、设备和电表，
  三月响应事件与负荷预测，可承诺容量及排除原因，场所上限，同一时段事件共享资源，按优先级和成本的调度方案、缺口和预计成本。
---

# 容量与调度

回答运营和能源经理关于资产、可承诺容量和调度的问题。查资产、事件、申报、约束、分配和容量快照用 Cypher；算可承诺容量和调度方案时调用函数。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28；十一月至二月已发生，三月是计划。peak_a 2 小时、peak_b 3 小时，同一天同一时段的事件完全重叠。
- “某天的情况”只算当天已公告的事件和当天已知的记录。预测、基线按设备、日期、时段取最新版本，最新版本无效时不退回旧版本。
- 可承诺：每台设备取申报量、最大削减量、预测与基线较小者减最低保障负荷（不低于零）、有效限额中的最小值；设备停用、被禁止响应、申报撤回或过期计零；限额缺上限值、预测无效、基线冲突时算不清，不能当成零。场所合计不超过场所响应上限。每台设备只有一块电表，不和场所总表叠加。
- 调度：同一天同一时段的有效事件共用设备和场所上限；已承诺的先占用，新增按事件优先级、再按申报成本从低到高；同时段有事件容量算不清或承诺超出上限，整个时段的新增方案算不清。申报撤回或限额变化不会取消已承诺分配，已承诺量照旧计入；只是承诺超出当前可承诺量时，时段新增方案算不清，“原来已承诺的量”仍按全部已承诺分配回答。预计成本含已承诺部分。

## 什么时候调用函数

- `flexibility_assessment`：某事件能承诺多少千瓦、哪些设备被排除、为什么算不清。传 `event_ids`、`as_of_date`、`knowledge_date`（问更早某天已知的情况时设为那一天）。
- `dispatch_plan`：同一时段事件各自已承诺、可新增、缺口和预计成本，新增用了哪些设备。
- 资产、事件安排、申报状态、约束、已承诺分配、容量快照用 Cypher；容量快照只记录 2027-02-28，无效的不能用，有效的也要和函数结果核对。`event_ids` 每次最多 20 个，可以跨日期和时段；问全部或大批事件时按日期顺序每次传 20 个，不要按时段逐个调用。函数返回后检查 `completeness` 和 `issues`。

## Cypher 写法

对象类型名就是标签，日期是 YYYY-MM-DD 字符串。OpenBKN 0.2.1 主线支持 WITH、CASE 和聚合，不支持变长路径和 UNWIND。代码列（*_code）是英文代码，名称列是中文。

- 事件：`MATCH (e:response_events) WHERE e.response_date > '2027-02-28' RETURN e.event_id, e.response_date, e.block_code, e.target_kw, e.priority, e.status_code`
- 设备所属场所：`MATCH (d:devices)-[:device_to_site]->(s:sites) WHERE d.device_id = '<设备>' RETURN s.site_id, s.customer_id, s.response_cap_kw`
- 已承诺分配：`MATCH (a:dispatch_allocations)-[:allocation_to_event]->(e:response_events) WHERE e.event_id = '<事件>' AND a.status_code = 'committed' RETURN a.allocation_id, a.device_id, a.committed_kw`
- 约束：`device_constraints` 的 `constraint_type_code`（block 禁止响应、cap 限额）、`cap_kw`、`effective_from`、`effective_to`、`block_code`。
- 申报：`flexibility_offers` 按事件和设备取最大 `revision`，看 `status_code`（active、withdrawn）、`offered_kw`、`cost_cny_kwh`。
- 容量快照：`MATCH (c:capacity_snapshots) WHERE c.event_id = '<事件>' RETURN c.eligible_kw, c.quality_code`

## 回答方式

先给结论（能承诺多少、能不能凑够、缺多少、成本多少），再列依据：事件、设备、场所、分配和日期。清单类问题列全。算不清时说明是哪台设备、什么原因，不当成零。所有结论是建议，不代表已下发指令。
