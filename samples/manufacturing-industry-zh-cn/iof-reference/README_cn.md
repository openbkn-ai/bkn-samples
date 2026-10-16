# IOF Core 与生产计划完整参考

## 上游开源来源

本参考层取自 [Industrial Ontologies Foundry 本体仓库](https://github.com/iofoundry/ontology)，固定采用 [IOF Core](https://spec.industrialontologies.org/portal/release/202603/core.html) 和 [Production Planning 模块](https://spec.industrialontologies.org/portal/release/202603/productionplanning/ProductionPlanningOntology.html)。IOF 在 [Core 源码](https://github.com/iofoundry/Core/blob/main/Core.rdf) 中声明 MIT 许可证；本包保留的来源 IRI 是术语级追溯的准据。

此目录是制造业行业样例内完整的 IOF 标准层。它覆盖固定 IOF 源文件中的全部具名类和具名对象属性：91 个 IOF Core 类声明、22 个 Production Planning 类声明（112 个唯一类 IRI），以及 83 个 Core 属性、4 个 Production Planning 属性（85 个唯一属性 IRI）。只有显式直接 domain 与 range 都恰为固定模块中一个具名类的属性才生成 BKN RelationType；其余属性完整保留在[未投影 OWL 属性清单](docs/unprojected-owl-relations_cn.md)中，不再连接到人为构造的兜底对象。

原 RDF 还包含 14 个 Core 和 8 个 Production Planning 匿名 `owl:Class` 限制表达式。它们没有独立 IRI、标签或可单独绑定的实例类型，因此不生成为 BKN ObjectType；它们的约束语义由来源 RDF 保留并在语义差异说明中记录。

`kn/` 为可离线校验的 BKN 目录。每个具名类对应一个 ObjectType。`data/` 目录为 112 个 ObjectType 中的每一个提供一张可追溯的合成参考实例 CSV，用于演示完整导入覆盖，不把每个 IOF 类都伪称为真实运营记录。ObjectType 中的 `source_iri`、`source_label`、`source_definition` 用于追溯。7 条直接 BKN 关系通过参考实例中的 `*_target_id` 字段关联；执行 `python3 tools/verify_reference_instances.py` 可核验覆盖与关系。

中文名称采用中文术语；为避免篡改 IOF 精确定义，`source_label` 和 `source_definition` 保留上游原文，并以固定 IRI 为准。

上级的 `kn/` 是包含 40 个对象的端到端制造运营模型，提供需求、供应、库存、生产、质量、人员和维护的运营数据；它不替代本目录的完整标准层。
