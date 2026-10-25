# 指标 V1 消费验收

从 `get_object_types` 返回的 `related_metrics` 发现所属对象类的已发布指标 ID 和明确版本，再根据定义确认指标身份。不要根据名称拼接 ID，也不要省略 version。

`tools/assets/metrics-consumption-examples.json` 提供真实锁定数据的查询与预期值。用其中的 query 调用 MCP `query_metric`，加上实际 kn_id、metric_id、version 和 response_format=json。供应链先查总值，再查仓库 Top 5；要声称全量时继续 next_cursor。快照指标按已给出的实例身份查值，并核对原始记录的日期与单位；不能当作实时重算或跨期合计。

将 MCP 框架的工具调用适配为 `call(tool_name, arguments)`，返回解析后的业务 JSON，错误直接抛出。`tools/metric_consumer.py` 的 query_all 读取全部页；metric_result 可检查单页 Top 5。participants_all 保留原始 query 和服务端 bucket_key，只有条目声明 participants 时才调用 drill_through_metric。游标和桶键均不能自行构造。

展示保留 model 中的单位与业务日期，数值优先使用 display_value。JSON 文本可用 json.loads(text, parse_float=Decimal) 解析以保留十进制精度。partial、warnings、unavailable 或未读完的分页不能作为完整成功；无数据和未知值不能替换成零。参与实例是当前求值证据，不是历史审计或逐行贡献分摊。

支持 MCP App 的客户端可以展示平台分析组件；其他客户端仍按相同结果给出准确文本或表格。样例不实现独立指标前端。本轮只完成本地合同和锁定数据检查，真实 0.2.1 MCP 验收尚待进行。
