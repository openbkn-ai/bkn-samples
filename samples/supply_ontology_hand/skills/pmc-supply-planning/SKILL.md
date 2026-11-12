---
name: pmc-supply-planning
description: >
  Use for PMC production-planning questions on knowledge network supply_ontology_hand:
  sales backlog and overdue orders, finished-goods stock, forecasts, BOM structure and
  where-used, how many sets can be built or promised, whether new orders or work orders
  are covered, which materials block them, and kit-schedule plans (which demand is
  scheduled on which line, its kit result, rescheduling and cancelling).
---

# PMC 生产计划

回答计划经理关于欠货、接单、排产和备料的问题。查数、汇总、追关系用 Cypher；需要按 BOM 逐层净扣时执行计算行动。

## 默认口径

使用者没有另说时，按以下口径回答，并在结论里简短说明用了哪条口径。

- 业务日期 2027-02-25，“现在、今天、当前”都指这一天。
- 库存只算库存状态为“可用”的 `available_inventory_qty`，默认全公司所有仓；“不良”库存不能投产、不能发货。“成品仓”是苏州成品仓、乌鲁木齐成品仓、哈尔滨成品仓；“苏州工厂生产七仓”是苏州半成品仓、苏州成品仓、苏州电子原料仓、苏州无人机原料仓、苏州装配原料仓、乌鲁木齐成品仓、哈尔滨成品仓。
- 欠货 = 签约数量 − 已发货数量 > 0；承诺交期早于业务日期即逾期。补发顺序按承诺交期，再按订单号。
- 在途 = 采购订单行关闭状态和终止状态都是“正常”，且订购数量 − 实收数量 > 0。交期不早于业务日期的按交期计入；交期早于业务日期的是逾期在途，不算确定供给，只在使用者说“假设能催回来”时计入。
- “现在、用现有库存能做多少”只看库存；问某个日期前投料或交货时，再加该日期前（含当天）按交期到货的在途。
- 生产可做数量按 BOM 逐层净扣：先用成品，再每层先扣组件库存、只展开净缺；多张需求共用一个库存池。默认不用替代料，使用者允许时才用。
- 可承诺量 = 成品库存 + 现有库存还能生产的数量 − 该产品已签约欠货。接新单、谈预测都要先保已签约欠货，结论只给先保欠货后的数，不另给不保欠货的对照。
- “成品库存”“现货”指产品自身的可用库存，默认全公司所有仓；只有使用者说“成品仓”时才限定三个成品仓。
- “现货”只指成品可用库存，不含还能生产的数量：现货还能承诺 = 成品可用库存 − 已签约欠货 − 本次要发的数量。
- 未关闭预测 = 关闭状态不是“已关闭”。一张预测单可以有多个产品，同一张单的产品同一天交货：交货日是 `startdate`（预测交货日期），`enddate` 是需求窗口结束日。交货日早于业务日期还没关闭的是已延期需求。现有库存能支撑多少预测按可承诺量算，不能只看成品库存。

## 什么时候执行计算行动

两个计算以行动提供：先用 `get_action_info` 取参数定义，再用 `execute_action` 执行，最后用 `get_action_execution` 取结果。每次都要传全部参数：替代料（默认 false）、仓范围（默认 all）、需求日期（不设时传空字符串）、是否计入逾期在途（默认 false）等是业务假设，用户没说时按默认值显式传入，并在回答里说明按什么假设算的。

- **产品可做数量与可承诺量**（`build_capacity`）：某产品现在最多还能做多少、可承诺多少、还能接多少新单、被哪颗料卡住；允许替代料、只用某几个仓、某日前在途到货、逾期在途催回后能多做多少。`products` 传产品编码列表，各产品独立计算；几个产品要一起看时一次传完，不要逐个调用。
  - 哪些产品的欠货靠现货和生产都补不上：先用 Cypher 找出欠货超过成品库存的产品，再把这些产品一次传给本行动，`finished_goods_qty + buildable_qty < signed_backlog_qty` 的就是补不上的，差额是 `signed_backlog_qty − finished_goods_qty − buildable_qty`（`available_to_promise` 最小为 0，不能用来判断）。
  - 某日前在途能让这些产品多做多少：同一批产品再传 `need_by` 调一次，两次 `buildable_qty` 相减。
- **需求齐套与缺料**（`demand_coverage`）：一张或几张需求够不够、缺哪些料、各缺多少。
  - 评估欠单本身：不传 `reserve_signed_backlog`。
  - 评估新单且要先保欠货：`reserve_signed_backlog=true`。
  - 排生产工单、不动成品：`use_finished_goods=false`。
  - 多单同时来：按使用者给的先后放进 `demands`。
- 其他问题（欠货、库存、预测、工单、BOM 清单、反查用途、通用料）用 Cypher，不要执行计算行动。函数的 `limiting_materials` 和 `shortages` 是最底层缺料；要回答这些料有没有在途、交期多久，再用 Cypher 查采购订单和物料。

## 齐套排产计划

排产结果记录在齐套排产计划（`supply_ontology_hand_kitplan`），需求预测单本身不改。一条计划对应一张预测单的整单（`product_code` 为空）或其中一个产品，排在一条产线上；同一预测单号 + 产品编码只有一条有效计划（`plan_status` 不是“已取消”）。

- 字段：计划号 `plan_id`、预测单号 `bill_no`、产品编码 `product_code`、产线 `line_code`、计划开工 `planned_start`、计划完工 `planned_finish`、数量 `quantity`（整单为空）、齐套状态 `kit_status`（齐套、缺料）、齐套日 `kit_date`、关键物料 `key_material`、缺料说明 `shortage_note`、计划状态 `plan_status`（已排、已确认、已取消；已确认表示已下达生产）、改期次数 `reschedule_count`、上次计划完工 `previous_finish`、来源方案 `source_scenario`、排产人 `planner`、排产时间 `planned_at`。
- 齐套结论是排产时按计划开工日算的：先保已签约欠货、不用成品、计入计划开工日前按期到货的在途，口径与“需求齐套与缺料”相同。齐套时齐套日是最早可开工日；缺料时齐套日是在途按期到货后能齐套的日期，为空表示现有在途补不齐。问“现在还够不够”时重新执行需求齐套与缺料，不要只看计划里记录的结论。
- 已排计划：`MATCH (k:supply_ontology_hand_kitplan) WHERE k.plan_status <> '已取消' RETURN k.plan_id, k.bill_no, k.product_code, k.line_code, k.planned_start, k.planned_finish, k.kit_status, k.kit_date, k.key_material, k.plan_status`。某张单排没排：加 `AND k.bill_no = '<预测单号>'`；没有有效计划就是待排。
- 产线在 `supply_ontology_hand_line`：工厂也是一行（`line_kind` 为“工厂”，不排产），产线的 `parent_code` 是所属工厂，`max_parallel` 是同时可执行的计划数，`product_lines` 是可生产的产品线；产品的默认产线是产品对象的 `line_code`。停线窗口在 `supply_ontology_hand_stoppage`，`resource_code` 是产线或工厂编码，工厂级窗口作用于该工厂所有产线。
- 只有使用者明确要求排产、改期或取消时才执行三个行动：“建立齐套排产计划”（新建实例，`object_input` 传 `bill_no`、`product_code`〔整单传空字符串〕、`line_code`、`planned_start`、`planned_finish`、`plan_status`〔通常为已排〕、`source_scenario`、`planner`）、“调整齐套排产计划”（修改实例，`_instance_identities` 传选中计划的 `plan_id`，再传新的产线、计划开工、计划完工、来源方案、排产人）、“取消齐套排产计划”（修改实例，传计划号和排产人）。执行前说明要写入什么；执行后从结果里报告计划号、齐套状态、齐套日和关键物料。重复建立同一单（同一产品）不会新增计划，会修改已有的那条。
- 问“这些计划现在排得通吗、哪张会缺料、产线能不能做”时，执行“齐套检查”“产线可生产”两个行动（排程甘特用的是同一套规则）：`tasks` 每条为 `{key, start, resource, values}`，key 用计划号，start 用计划开工，resource 用产线编码，values 带 `bill_no`、`product_code`、`line_code`、`planned_start`、`plan_status`。齐套检查把所有传入的计划放在同一库存池里按开工先后分配，所以要一次传入相关的全部计划；`related` 是争同一物料的计划。

## Cypher 写法

对象类型带前缀 `supply_ontology_hand_`，例如 `supply_ontology_hand_salesorder`。日期是 `YYYY-MM-DD` 字符串，直接比较大小。平台不支持变长路径和 `UNWIND`。

- 欠货：`MATCH (s:supply_ontology_hand_salesorder) WHERE s.signing_quantity > s.shipping_quantity RETURN s.sales_order_id, s.customer_name, s.product_code, s.signing_quantity - s.shipping_quantity AS owed, s.promised_delivery_date`
- 成品或物料库存：`MATCH (i:supply_ontology_hand_inventory) WHERE i.material_code = '<编码>' AND i.stock_status = '可用' RETURN sum(i.available_inventory_qty)`；限定仓库时加 `AND i.warehouse IN [...]`。
- 整棵 BOM：从产品一次取全，`bom_level` 为 0 是产品自身，主料行 `alt_priority = 0`。`MATCH (p:supply_ontology_hand_product {material_number: '<产品>'})-[:supply_ontology_hand_prod2bom]->(b:supply_ontology_hand_bom) WHERE b.bom_level > 0 AND b.alt_priority = 0 RETURN DISTINCT b.material_code`；一级物料加 `b.bom_level = 1`。
- 反查用途：`MATCH (b:supply_ontology_hand_bom) WHERE b.material_code = '<物料>' AND b.alt_priority = 0 AND b.bom_level > 0 RETURN DISTINCT b.bom_material_code`
- 两个产品的通用料：分别 `collect(DISTINCT b.material_code)` 成列表 `a`、`b`，`RETURN size([x IN a WHERE x IN b])`。
- 未关闭预测：`supply_ontology_hand_forecast`，`closestatus_title <> '已关闭'`，数量 `qty`，产品 `material_number`。
- 生产工单：`supply_ontology_hand_mps`，任务状态 `taskstatus_title`（完工、开工、部分完工、未开工），未入库 = `qty - xkquainwaqty`。
- MRP 计划订单：`supply_ontology_hand_mrp`，`dropstatus_title = '未投放'`。
- 产品线和上架状态在物料对象：`supply_ontology_hand_material` 的 `huid_productline_name`、`product_status`。

## 回答方式

先给结论（能不能、多少、差多少），再列依据：用到的口径、订单或物料清单、关键数量。清单类问题列全，不截断。数据里查不到或口径不明确时直接说明，不猜数。所有结论是计划建议，不代表已经下单或发货；只有执行了齐套排产计划行动才算排产。
