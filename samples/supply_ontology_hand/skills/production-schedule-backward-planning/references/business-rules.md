# 业务规则：生产计划倒排 · 齐套诊断

本文件是 S1 包内的倒排、供应状态和 A/B 延迟口径。已发布的生产计划齐套倒排函数按本口径自行读取知识网络并计算；Agent 不在本地复算。

输入粒度：一个产品 + 一张需求预测。

## 1. 倒排时间

日历日；日期 `YYYY-MM-DD`。

| 步骤 | 公式 |
|------|------|
| L0 end | `demand_end` |
| L0 start | `demand_end - product_fixedleadtime`（天） |
| 子件 end | `parent.start - 1` 天 |
| 标准提前期 | 外购/委外：`purchase_fixedleadtime`；自制：`product_fixedleadtime`；缺失按 0，条长再用 `max(., 1)` |
| 供应合计 | `available_inventory_qty + in_transit_qty`（有效仓口径） |
| 是否已满足（条长启发式） | `!hasMRP && supply > 0` |
| 甘特条长 | 已满足 → 1；否则 `max(standardLeadtime, 1)` |
| 子件 start | `child_end - ganttLeadtime` |

BOM：默认主料（`alt_priority == 0` 且 `alt_method != 替代`）；按 `parent_material_code` 建树；环路跳过；上限 5000 节点。

在途只计未关闭 PO：`max(0, qty − actqty)`。PR 未清只进 10 档，不进供给量。

## 2. 供应状态（顺序匹配，S1 内部）

无到位日 → `unknown`，不要判档。

```
supply = available + in_transit
if supply >= grossRequirement → sufficient

if 外购 or 委外:
  if !hasMRP → anomaly
  if has_po and poDeliverDate:
    if poDeliverDate <= business_date → po_overdue
    if poDeliverDate > endDate → deadline_risk
  if not has_po:
    if standardLeadtime > days_until(endDate) → deadline_risk
  if no_pr → no_pr
  if has_pr and no_po → no_po
  → po_in_transit

if 自制:
  if hasShortage → child_short
  if !hasMRP → unscheduled
  → plan_gap
```

| 等级 | 状态 |
|------|------|
| danger | anomaly, deadline_risk, po_overdue |
| warning | no_pr, no_po, child_short |
| info | unscheduled, plan_gap, po_in_transit |
| normal | sufficient |

## 3. A/B 延迟

仅 `bom_level > 0`；同料号保留最大延迟。

**A 类**：外购/委外；`start < business_date`；无 PO；库存不满足；`delayDays = max(0, (business_date + LT) − end)`。

**B 类**：有 PO 且 `poDeliverDate > end`。

产品级：`maxDelayDays = max(A∪B)`；`canDeliverOnTime = (maxDelayDays == 0)`。

## 4. 边界

- 倒排树、A/B、10 档 → 本 Skill
- 盘子规模 / 库存合计 → Metric
- 现在能卖多少 → S2（不要在本 Skill 算合计可售）
- 后续处置仅输出人工建议；本版本不创建监控、采购申请、采购订单或 ERP 记录
