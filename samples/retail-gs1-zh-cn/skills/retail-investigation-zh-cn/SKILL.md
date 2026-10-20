---
name: retail-investigation-zh-cn
description: 食品追溯、库存履约、未来补货及召回的只读调查。
---

先明确业务日期、知识截止日、商品/地点、实际库存或未来计划。通过search_capabilities发现真实函数与指标，不猜ID；先读本Skill附带的business-contract.md。

1. 主数据用对象查询；库存、效期、质量、追踪用inventory_asof；共享库存履约和未来补货用fulfillment_plan；召回范围和处置用recall_assessment。模式、范围和字段见契约。
2. 检查工具isError、exit_code、非空result、completeness和issues。未知保持null；不能用快照替代失败重算。原子查询必须完整分页；日期过滤值按工具契约，不猜时区。
3. 两个指标recorded_available_quantity和recorded_recall_coverage只对应一个已记录快照实例；核对日期、知识截止日、商品、地点/召回和单位。不跨期求和。
4. 使用精确Decimal和六位数量/比例，不混加商品单位；事件去重、撤销、迟报与隔离重叠按公开函数处理，不自行复制复杂规则。
5. 每个run_code至多调用一个已发布函数。只投影所需字段、证据和异常；不要把大量前次JSON重新嵌入代码。需要跨函数时分别调用。计划到货不算实际库存。
6. 用中文解释业务含义，类型化status_code保持稳定代码；列出来源ID、范围、不确定性和只读建议。不得实际下单、出库或发召回通知。
