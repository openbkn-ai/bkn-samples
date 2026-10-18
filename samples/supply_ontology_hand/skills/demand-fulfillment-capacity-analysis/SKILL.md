---
name: demand-fulfillment-capacity-analysis
description: >
  Use when analyzing how many finished units can be sold now (成品仓 + 理论可产)
  on knowledge network supply_ontology_hand. Not a delivery-date promise.
---

# 需求承接 · 产品可售能力（S2）

这是一个**业务场景导航 Skill**。只问一个确定数值时可直接调用函数；当用户还需要解释可售能力含义、库存组成或与交期承诺的区别时使用本 Skill。

> 三个数必须分开：**理论可产 ≠ 合计可售 ≠ 齐套净需求**。本 Skill 只回答合计可售，结果不是交期承诺。

## Skill Card

| 字段 | 值 |
|------|-----|
| `bkn_scope` | `supply_ontology_hand` |
| `trigger` | 现在最多能卖多少、可售能力、理论可产+成品库存 |
| `required_metrics` | 库存可用量（成品仓 `finished_goods` + 生产仓 `production_available`） |
| `calculation` | **合计可售**（`total_sellable`，返回成品库存、理论可产和合计可售） |
| `优先指标` | 库存可用量（用于解释成品仓或生产仓事实） |
| `优先函数` | **合计可售**；必要时配合 **理论可产**、**子料分层库存** |
| `open_parameters` | `product_query`、`substitute_enabled`、`production_scope?`、`finished_goods_scope?` |

不要调用：净需求/齐套、供应状态 10 档、共用料争用 / S3。在途 PO 可作对照，**不得**加入合计可售。

## Agent 执行步骤

1. 解析唯一产品；名称存在歧义时先澄清编码或型号。
2. 确认替代料策略和仓范围；未确认替代策略时不输出确定数量。
3. 调用 **合计可售**，直接使用函数返回的成品可用、理论可产和总可售结果。
4. 需要解释瓶颈或库存分布时，再调用 **理论可产** 或 **子料分层库存**。
5. 明确说明：合计可售是当前静态能力，不等于某个日期的履约承诺；日期承诺转 S1。

## 业务边界

- `total_sellable` 同时返回成品仓可用、理论可产和合计可售，Skill 不在本地重算
- 理论可产不含成品、不加在途；合计可售包含成品仓可用，但仍不加在途
- “要 X 套齐不齐”属于齐套净需求；“某日能否交付”属于 S1，不能用可售结果替代
- 未给出 `substitute_enabled` → 先问再算；未确认返回不能算

## 计算调用

用户输入先解析为唯一产品编码。业务公式由已发布函数执行，函数自行读取 BKN 数据；Agent 不读取 Skill 源码、不重建运行时、不在本地重算函数结果。

## 输入

- `knowledge_network_id`：默认 `supply_ontology_hand`
- `product_query`：必填；允许产品编码或名称，名称命中多个编码时必须追问；解析后以 `product` 传给函数
- `substitute_enabled`：未给出则询问「是否启用替代料核算？（是/否）」
- `finished_goods_scope`：默认 `finished_goods`；`production_scope`：默认 `production_available`
- 必须回显函数实际返回的两套仓范围；不得凭 Skill 文本伪造仓名单

## 编排

1. `resolve_input` — 解析唯一产品，确认替代料及仓范围
2. `select_capability` — 简单数量直调函数；需要解释业务边界时使用本 Skill
3. `analyze` — 调用合计可售，必要时补充理论可产或分层库存
4. `render_report` — 输出 Markdown 并声明不是交期承诺

## 完成门槛

1. 产品已解析为唯一编码；BOM 非空，或函数明确返回无法计算
2. `substitute_enabled` 已确认
3. 成品仓名单与生产仓名单按函数结果回显
4. 出参含 `fg_qty` / `theoretical_build_qty` / `total_sellable_qty`
5. 报告阶段不再拉数或重算

## 输出

1. `analysis_result`：见 `references/io-contract.md`
2. 完整 Markdown：见 `references/report-spec.md`

## 参考

- `references/business-rules.md`
- `references/io-contract.md`
- `references/report-spec.md`
