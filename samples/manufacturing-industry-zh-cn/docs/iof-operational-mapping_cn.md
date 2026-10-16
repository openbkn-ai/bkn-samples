# IOF 与运营模型映射

运营网络是 BKN 的运营扩展层，不是第二份 IOF 副本。下表是可执行的设计规则：列出的运营记录以业务主键作为 BKN 键，所列来源 IRI 是语义锚点；未列出对应 IOF 类的项目明确标为运营扩展。

| 运营 ObjectType | IOF 来源类／状态 | 字段映射与转换规则 |
|---|---|---|
| `products` | `MaterialProduct` — `https://spec.industrialontologies.org/ontology/construct/MaterialProduct` | `product_id` 为本地主键；产品编码、名称、类型和单位为运营属性。 |
| `production_orders` | `ProductionOrder` — `https://spec.industrialontologies.org/ontology/construct/ProductionOrder` | `production_order_id` 为本地主键；产品、数量、交期和状态将 IOF 目标规格落为运营字段。 |
| `manufacturing_operations` | `ManufacturingOperation` — `https://spec.industrialontologies.org/ontology/construct/ManufacturingOperation` | `operation_id` 为本地主键；工作中心和状态为运营计划属性。 |
| `process_steps` | `ProcessStep` — `https://spec.industrialontologies.org/ontology/construct/ProcessStep` | `process_step_id` 为本地主键；`required_capability_id` 为 BKN 需求扩展。 |
| `production_machines` | `ProductionMachine` — `https://spec.industrialontologies.org/ontology/construct/ProductionMachine` | `machine_id` 为本地主键；基地、工作中心和状态为运营属性。 |
| `equipment_capabilities` | `Capability` — `https://spec.industrialontologies.org/ontology/construct/Capability` | `capability_id` 为本地主键；分类为本地能力目录属性。 |
| `customers`、`suppliers`、`operators` | 可用时锚定 IOF 的商业／主体概念 | 客户、供应商和操作员 ID 为本地主数据键；商业和雇佣字段为扩展。 |
| 其余 31 个 ObjectType | BKN 运营扩展 | BOM、工艺路线、订单行、库存、执行、检验结果、班次、资质和维护是可导入 ERP/MES 运营所需内容；外键已声明为 71 条 BKN RelationType。 |

核心关系映射：`production_orders.product_id → products.product_id`；`manufacturing_operations.production_order_id → production_orders.production_order_id`；`process_steps.operation_id → manufacturing_operations.operation_id`；`process_steps.required_capability_id → equipment_capabilities.capability_id`；`production_execution_records.process_step_id → process_steps.process_step_id`；`quality_inspection_lots.production_order_id → production_orders.production_order_id`。这些映射由 `tools/verify_industry_links.py` 核验。
