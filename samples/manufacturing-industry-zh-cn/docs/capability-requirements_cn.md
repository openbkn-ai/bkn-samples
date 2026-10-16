# 制造业样例：指标、函数与 Skill 需求

## 目的与边界

样例支持从已下达计划快照开始，经 BOM 可追溯的发料、生产、最终质量、成品入库到发运的制造履约判断。它使用 40 张运营表、71 条直接关系和可确定复算的事务证据；不宣称支持有限产能排程、派工优化、批次谱系或根因处置。

## 指标

| ID | 指标 | 定义 | 粒度 |
|---|---|---|---|
| `material_issue_coverage` | 发料覆盖率 | `issued_quantity / required_quantity` | 工单物料需求 |
| `available_inventory` | 可用库存 | 库存余额 `as_of_date` 时的 `on_hand_quantity - allocated_quantity` | 产品和库位 |
| `final_quality_conformance` | 最终质量符合性 | 最终检验批已接受，且结果位于关联规格限值内 | 工单 |
| `shipment_eligibility` | 发运资格 | 订单、已接受成品入库、已接受最终检验和数量全部一致时才可完成发运 | 发运 |

## 确定性函数

### `evaluate_work_order_fulfillment`

**输入：** `production_order_id`。

**处理：** 追溯已下达计划行、冻结的 BOM 版本与组件、物料需求与发料、执行与最终检验、成品入库、库存快照和发运；复算四项指标并返回稳定证据 ID。

**输出：** `fulfilled`、`blocked`、`quality_rejected`、`pending` 或 `unknown`，并给出首个未通过闸门及其证据。

### `evaluate_shipment_gate`

**输入：** `shipment_id`。

**检查：** 订单/入库/检验一致性、数量边界、完成发运的质量与入库接受状态，以及阻塞、拒绝、待处理分支的零发运数量。

**输出：** `eligible: boolean`、履约状态、失败原因码和来源记录 ID。

## Skill

### `analyze_manufacturing_fulfillment`

回答计划或工单能否履约的业务问题。它调用两个函数，以请求语言呈现模型可证明的结论；证据不足时明确缺失事实，不编造排程、采购或维护建议。

## 验收

`WO-1001` 可履约：122/122 已发料、最终检验已接受、120 件成品已入库且 120 件已完成发运。物料短缺工单在 2027-03-31 快照上的原料可用库存为零，不能发运；质量拒绝和待处理分支同样保持零发运数量。MFG-18 对 50 条发运逐条验证这些闸门。
