---
name: energy-response-investigation-zh-cn
description: 只读需求响应能力、共享资源方案、计量交付及结算调查。
---

先阅读 [业务能力合同](references/business-capability-contract.md)。这是只读合成需求响应调查，不执行设备控制、响应指令或付款，也不声称全局最优。

1. 明确 event_ids（1至20个不同主键）、as_of_date 和 knowledge_date；日期均为 YYYY-MM-DD。不清楚范围时先停止推算并澄清，不能猜测日期或主键。用 search_capabilities 发现实际能力标识。
2. 可用能力与约束调查调用 flexibility_assessment；共享设备及场所容量的确定性只读增量方案调用 dispatch_plan；执行回执、实际计量、补偿门槛和台账差异调用 settlement_assessment。完整重叠事件池由函数处理，不能因只问一个事件而重复使用资源。
3. 每次 run_code 最多调用一个原生函数。检查 isError、exit_code、非空返回、completeness、issues；发生缺失或冲突时保留 null 和来源证据，停止给出依赖未知值的确定结论。失败不能用快照补成完整答案。
4. recorded_eligible_kw 对应 capacity_snapshots.eligible_kw（kW）；recorded_delivery_ratio 对应 settlement_snapshots.delivery_ratio（无量纲1）。两者均为单个事件、业务日期、知识截止日期的已记录快照。精确匹配事件和日期，检查快照 quality_code；逐实例核对重算结果并解释差异，不能跨日期求和或当作实时重算。
5. 功率 kW 是响应块平均减载；电量 kWh=功率×块小时。金额 CNY 保留两位，数量与比例保留六位，四舍五入；不能从块平均数推断逐时安全性。未来结算 not_due；cancelled 为取消；unknown 不是零。
6. 每个问题按 event_ids 区分所问事件与完整重叠池事件；问题码必须注明受影响事件、来源ID及业务后果。共享池其他事件的拒绝或支付阈值问题不能归到所问事件；需要解释原因时按来源ID核查原始申报、承诺或回执。
7. 比较知识截止日期时分别给出主视图与参考视图的范围、结果、问题和来源证据，再说明变化原因。事件尚不可见必须直说；若参考视图可读取该事件，核查 announced_date 和 known_date，给出具体日期并说明哪条可见性条件不满足，不能将参考事实冒充早期可见信息。不用零或后一视图来源填补；撤回使原承诺失效时，说明已知承诺仍保留、新方案为何未知。
8. 跨能力、计划、计量、结算调查时分别列出各阶段 completeness、受影响事件和阻塞原因。结算 complete 不代表计划完整；只要某个必要阶段 partial，端到端结论必须指出该缺口。快照差异明确说明重算减快照的值和单位。原始收尾/留痕错误独立报告，不能被业务完整性覆盖。
9. 来源引用保留每次实际调用的完整 evidence；主视图与参考视图分别标注，合并索引仅作辅助，不凭空补来源。
10. 用中文说明业务事实，保留稳定英文主键、status_code 与问题码。引用来源ID、日期范围、缺失信息、测量去双计逻辑和可读建议。只给建议，不发控制指令、不转账、不付款。
