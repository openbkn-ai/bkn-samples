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

## 指标 V1 消费验收

从 `get_object_types` 返回的 `related_metrics` 发现所属对象类的已发布指标 ID 和明确版本，再根据定义确认指标身份。不要根据名称拼接 ID，也不要省略 version。

`tools/assets/metrics-consumption-examples.json` 提供真实锁定数据的查询与预期值。用其中的 query 调用 MCP `query_metric`，加上实际 kn_id、metric_id、version 和 response_format=json。供应链先查总值，再查仓库 Top 5；要声称全量时继续 next_cursor。快照指标按已给出的实例身份查值，并核对原始记录的日期与单位；不能当作实时重算或跨期合计。

将 MCP 框架的工具调用适配为 `call(tool_name, arguments)`，返回解析后的业务 JSON，错误直接抛出。`tools/metric_consumer.py` 的 query_all 读取全部页；metric_result 可检查单页 Top 5。participants_all 保留原始 query 和服务端 bucket_key，只有条目声明 participants 时才调用 drill_through_metric。游标和桶键均不能自行构造。

展示保留 model 中的单位与业务日期，数值优先使用 display_value。JSON 文本可用 json.loads(text, parse_float=Decimal) 解析以保留十进制精度。partial、warnings、unavailable 或未读完的分页不能作为完整成功；无数据和未知值不能替换成零。参与实例是当前求值证据，不是历史审计或逐行贡献分摊。

支持 MCP App 的客户端可以展示平台分析组件；其他客户端仍按相同结果给出准确文本或表格。样例不实现独立指标前端。本轮只完成本地合同和锁定数据检查，真实 0.2.1 MCP 验收尚待进行。
