---
name: manufacturing-production-quality-zh-cn
description: >
  用于知识网络 manufacturing_industry_zh_cn 上生产主管和质量经理的问题：产品 BOM、工艺路线、设备能力和操作员资质，
  工单进度、完成数量、报废与良率，执行是否合规（设备能力、保养当天、人员资质、排班），检验拒收、超限、质量漏检和规格版本，设备维护逾期与维修。
---

# 生产与质量

回答生产主管和质量经理的问题。本样例没有函数，全部用 Cypher 查询后按下面的口径判断。

## 默认口径

使用者没有另说时按以下口径回答，并在结论里简短说明用了哪条。

- 业务日期 2027-02-28；十一月至二月已发生，三月工单是计划。
- 执行合规，每条执行四项都要满足，任何一项不满足即不合规，要说明是哪一项：
  1. 设备对该步骤要求能力（`required_capability_id`）的能力状态为合格；
  2. 设备在执行开始日（`started_date`）没有维护工单；
  3. 操作员对该能力的资质为合格，且有效期（`valid_to`）不早于开始日；
  4. 操作员在覆盖开始日的周班次里，被安排在该工序的工作中心。
- 工单完成数量 = 最后一道工序的合格数；工序良率 = 合格 ÷ (合格 + 报废)；工单良率 = 完成数量 ÷ 工单数量。
- 质量放行：检验批已接受，且每项测量值在所引用规格（`quality_specification_id`）的上下限之内（含边界）。结果记为通过但测量值超限按不合格计，是质量漏检，要说明这批是否已发货。问产品现行规格看状态为生效的那条，旧版本状态为已作废。
- 维护：计划日期早于业务日期且未完成的维护工单为逾期；维修中的设备不能排产；能力状态为暂停的设备不能做该能力的活。
- 现在能上某项能力的操作员：资质合格、有效期不早于业务日期、在职。

## Cypher 写法

对象类型名就是标签，关系类型名是“源表_外键_to_目标表”。日期是 YYYY-MM-DD 字符串。OpenBKN 0.2.1 主线支持 WITH、CASE 和聚合，不支持变长路径和 UNWIND。状态取值是中文（合格、暂停、培训中、在职、离职、已安排、已计划、进行中、已完成、已接受、已拒绝、待处理、通过、不通过、生效、已作废、可用、维修中）。

- 执行到工单：`MATCH (e:production_execution_records)-[:production_execution_records_process_step_id_to_process_steps]->(s:process_steps)-[:process_steps_operation_id_to_manufacturing_operations]->(o:manufacturing_operations) RETURN e.execution_record_id, e.machine_id, e.operator_id, e.started_date, e.good_quantity, e.scrap_quantity, e.status, s.required_capability_id, o.work_center_id, o.production_order_id, o.sequence_number`
- 设备能力：`machine_capability_assignments` 的 `machine_id`、`capability_id`、`qualification_status`；设备状态在 `production_machines.status`。
- 人员资质：`operator_qualifications` 的 `operator_id`、`capability_id`、`qualification_status`、`valid_to`；在职状态在 `operators.employment_status`。
- 排班：`MATCH (a:operator_shift_assignments)-[:operator_shift_assignments_shift_id_to_shifts]->(t:shifts) RETURN a.operator_id, a.work_center_id, t.starts_date, t.ends_date`（每个班次是一周）。
- 维护：`maintenance_work_orders` 的 `machine_id`、`planned_date`、`status`。
- 检验：`MATCH (r:quality_inspection_results)-[:quality_inspection_results_inspection_lot_id_to_quality_inspection_lots]->(l:quality_inspection_lots) RETURN l.inspection_lot_id, l.production_order_id, l.status, l.lot_quantity, r.characteristic_name, r.measured_value, r.lower_limit, r.upper_limit, r.result_status, r.quality_specification_id`
- 规格：`quality_specifications` 的 `product_id`、`characteristic_name`、`lower_limit`、`upper_limit`、`effective_date`、`status`。
- BOM 与工艺：`product_bom_versions`（状态已冻结为现行）、`bom_components`；`routings` 与 `routing_operations`（`sequence_number`、`work_center_id`、`required_capability_id`）。
- 是否已发货：`shipments` 按 `production_order_id` 汇总 `shipped_quantity`，客户经 `sales_order_line_id` → `sales_order_lines` → `sales_orders.customer_id`。

## 回答方式

先给结论（合不合规、良率多少、能不能放行、哪些逾期），再列依据：执行、设备、人员、班次、检验结果、规格和日期。清单类问题列全，不合规要逐条写出执行记录、所属工单和原因；先列清单再计数，结论里的条数必须与清单一致。所有结论是建议，不代表已放行、派工或停机。
