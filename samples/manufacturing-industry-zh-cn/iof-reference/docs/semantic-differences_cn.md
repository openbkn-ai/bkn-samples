# IOF 与 BKN 的表达边界

1. 此参考层覆盖固定源文件的全部具名类和对象属性，不覆盖 IOF 仓库其他模块，也不把其导入的 BFO、QUDT、OMG Commons 等外部本体复制为 BKN 条目。
2. OWL 的 subclass、equivalentClass、disjointWith、some/all/min/max cardinality、property chain、inverse property、transitive/symmetric property 及一阶逻辑注解不能由当前 BKN 格式等价表达或自动执行。它们保留在上游 RDF；BKN 正文记录 IRI、标签和自然语言定义。
3. 一个全局 OWL ObjectProperty 的 domain/range 可能为空、使用匿名联合/限制类，或落在未导入的外部本体。它会保留在[未投影 OWL 属性清单](unprojected-owl-relations_cn.md)中，但不会生成 BKN RelationType，因为 BKN 需要具体端点。这样不会凭空构造兜底业务对象，也不会收窄 OWL 原有语义。
4. 为使 BKN 直接关系具有可映射字段，生成的源 ObjectType 增加 `<property>_target_id`。这是 BKN 数据投影字段，不是 IOF 原本的 DatatypeProperty，也不修改 IOF 模型。
5. `entity_id`、`source_iri`、`source_label`、`source_definition` 是参考目录所需的追溯字段。后续业务样例的数据模型可以扩展它们，但不能把它们误认为 IOF 对所有实体施加的数据要求。
