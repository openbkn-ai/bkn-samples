# 本体层与运营数据层

本包包含两个用途不同的 BKN 网络。

| 层 | 位置 | 覆盖范围 | 用途 |
|---|---|---:|---|
| IOF 标准参考模型 | `iof-reference/kn/` | 112 个 ObjectType、85 个具名 OWL 对象属性 | 对固定 IOF Core 与 Production Planning 来源的完整结构投影。7 个端点可在固定模块内精确确定的属性生成 BKN RelationType，其余 78 个保留在 OWL 属性清单中。 |
| 制造运营模型 | `kn/` | 40 个 ObjectType、71 个 RelationType | 可导入的端到端样例数据，覆盖需求、供应、库存、生产、质量、人员和维护。 |

运营模型的核心概念映射到 IOF 层：`products`、`production_orders`、`manufacturing_operations`、`process_steps`、`production_machines` 和 `equipment_capabilities` 分别对应 IOF 的 Product、ProductionOrder、ManufacturingOperation、ProcessStep、ProductionMachine 和 Capability。其余 ObjectType 是让行业链路可导入、可查询的明确运营扩展。

因此，40 张表不是对 112 个 IOF 类的替代；它们是使用该标准参考模型的、有实际数据的端到端业务层。
