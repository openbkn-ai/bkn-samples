# 指标查询与验收

样例提供 11 个标准 Object Metrics V1 对象集合指标。指标先创建草稿、校验，再发布；所有查询固定 `metric_id` 和 `version`。源定义见 `metrics-create.json`，查询见 `metrics-query-examples.json`。

这些指标表示对象集合的汇总，不是单个对象的逻辑属性。`power_layer.py verify-ownership` 核对已发布版本、所属对象类及对象类存在性，不把集合总量写成实例逻辑属性；函数逻辑属性不受影响。

```sh
python tools/power_layer.py all --kn-id supply_ontology_hand
```

未关闭预测数量查询显式使用 `closestatus_title != 已关闭`，按已发布的分析维度过滤。库存仓范围也由查询传入。过滤采用标准 V1 `filter` 和类型化属性引用。

`metrics-analysis-examples.json` 保留完整月查询和月对比：按 Asia/Shanghai 的每个自然月左闭右开边界调用真实指标，再计算相邻月差值。分组占比由真实完整分组结果计算，验收核对所有分组、各月值及 CSV 基准，不把缺失、部分结果或空结果视为成功。这些客户端运算不是额外发布的指标。

```sh
python tools/power_layer.py verify --kn-id supply_ontology_hand --query-file tools/assets/metrics-analysis-examples.json
```
