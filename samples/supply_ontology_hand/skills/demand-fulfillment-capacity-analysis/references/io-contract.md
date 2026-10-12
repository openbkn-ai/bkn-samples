# 输入输出契约：产品可售能力

输入：唯一产品、已确认替代策略；成品和生产仓范围缺省均为 `all`。显式预设或仓名单不得替换。通过 MCP 发现参数类型和函数后调用 **合计可售**。

出参使用函数实际字段：`fg_qty`、`theoretical_build_qty`、`total_sellable_qty`、`finished_goods_filter`、`production_filter`、替代开关及 `include_in_transit=false`。空仓筛选列表在全仓口径下表示不限制，报告同时回显 `all`。

需要瓶颈诊断调用 **理论可产**；逐料证据使用支持的完整粒度，并完整读取分页。不在契约中硬编码示例数值、仓名单或金标。能力不支持新口径时保留错误/限制，并输出无法确认。
