---
name: production-schedule-backward-planning
description: >
  Use when performing BOM-level production schedule backward planning (齐套倒排),
  material need-by dates, A/B delay classification, or supply-status diagnosis
  against a demand end date on knowledge network supply_ontology_hand.
---

# 生产计划倒排 · 齐套诊断（S1）

这是一个**业务场景导航 Skill**，不是每次查询都要使用的执行入口。只有出现“某产品、某数量、某截止日能否交付”“齐套倒排”“延期风险”等多步骤问题时才使用。

只问单个物料提前期时直接调用 **标准交期**；只问当前可售或可产数量时直接调用 **合计可售** 或 **理论可产**。

## Skill Card

| 字段 | 值 |
|------|-----|
| `bkn_scope` | `supply_ontology_hand` |
| `business_goal` | 按需求截止日完成 BOM 齐套倒排与交期风险诊断 |
| `user_persona` | PMC / 计划员 |
| `trigger` | 齐套倒排、生产计划倒排、A/B 延迟、物料到位时间 |
| `required_metrics` | 库存可用量（仓预设 `production_available`）；预测需求量合计（对照） |
| `calculation` | **生产计划齐套倒排**（`backward_plan` 业务口径）；对照可用 BOM 清单、子料分层库存、标准交期 |
| `优先指标` | 库存可用量、预测需求量合计（用于事实核对，不替代倒排） |
| `优先函数` | **合计可售**（先确认成品现货）；需要生产排程时用 **生产计划齐套倒排**；必要时配合 **要 X 套净需求与齐套**、**标准交期**、**供应状态诊断** |
| `open_parameters` | `product_query`、`forecast_id`、`demand_end`、`demand_qty`、`business_date?`、`warehouse_scope?`、`substitute_enabled`、`report_grain?` |
| `output_boundary` | 只输出交期风险与人工处置建议；不创建监控、采购申请、采购订单或 ERP 记录 |

无截止日不下交期结论。

## Agent 执行步骤

1. 用 Context Loader 查询并确认产品唯一性；名称命中多个产品时先澄清，不任选一个。
2. 确认数量、截止日和替代料策略；缺少任一关键条件时说明无法做交期承诺。
3. 先调用 **合计可售**，读取其中的成品可用量。若**成品现货已覆盖**客户需求，可直接答复能够按时交付，并说明交付后余量；此时**不调用 `生产计划齐套倒排`**，因为无需启动制造链。
4. 只有成品现货不足、客户明确要求生产排程，或需要解释生产与采购日期风险时，才从已发布工具列表选择 **生产计划齐套倒排**。有预测单时一并传入；新增客户需求可只传产品、数量和截止日。
5. 倒排函数不可用或未覆盖时，依次调用 **要 X 套净需求与齐套** 与 **标准交期**，仅基于函数返回结果说明“无法确认”或风险原因；不得重建计算公式。
6. 用业务语言输出结论：能否承诺、关键物料、日期风险、使用的仓范围和假设。需要后续跟踪时，只给出人工处置建议，不调用写入能力。

## 输入

- `knowledge_network_id`：默认 `supply_ontology_hand`
- `product_query`：必填，允许产品编码或名称；名称命中多个编码时先追问
- `forecast_id`：可选；已有预测单时传入以核对需求，新增客户需求可不传
- `demand_end`：YYYY-MM-DD，必填
- `demand_qty`：必填
- `business_date`：YYYY-MM-DD，可选；默认 `2026-08-25`，作为延期和供应状态的统一基准日
- `warehouse_scope`：默认 `production_available`；允许 `finished_goods` / `all` / 显式仓列表，必须回显
- `substitute_enabled`：未给出时先确认
- `report_grain`：`summary`（默认）/ `full_tree`

业务日期是样例口径，不使用服务器当天。替代策略未确认时，报告应说明前提不足而不作数量或交期承诺。

## 计算口径

倒排规则见 `references/business-rules.md`，输入与输出见 `references/io-contract.md`。函数自行读取知识网络，Skill 不读取源码、不重建运行时、不在本地计算业务算法。核心规则：

1. L0 以 `demand_end` 倒排产品固定提前期；子件结束日为父件开始日前一天。
2. 外购/委外按采购提前期，自制按生产提前期。
3. 有效供给为有效仓可用库存与未关闭 PO 未清量；PR 影响风险判断，不计入供给量。
4. A 类为已过开工日、无 PO 且库存不足的外购/委外物料；B 类为 PO 到货日晚于需求日的物料。
5. 成品现货已覆盖需求时，可按成品直发作出交付结论；此时不把制造倒排风险当作现货交付否决条件。
6. 成品现货不足而进入生产模式时，交期结论以最长延迟为准；合计可售不替代该生产倒排。

## 输出

1. `analysis_result`：产品、预测单、需求日、业务日期、仓口径、是否可按期交付、最大延迟、A/B 风险、供应状态摘要和缺口。
2. Markdown 报告：结论、关键物料、计算口径和数据前提。

如需后续跟踪，只给出人工处置建议；本版本不创建任何业务记录。

## 参考

- `references/business-rules.md`
- `references/io-contract.md`
- `references/report-spec.md`
- `references/kn-metrics.md`
