---
name: ecommerce-ops-zh-cn-finance-analysis
description: 电商经营与财务分析：当用户要核对订单应付、确认收款、退款申请与已完成退款、退款后净收款，或分析用户消费分层和金额/日期口径时使用。仅只读分析；不处理退款执行、支付发起或完整历史利润核算。
version: 1.1.1
lifecycle_state: active
---

# 经营与财务分析

## 运行约定

从当前对话或所选网络取得kn_id；缺失时先定位网络，不能猜测、固定使用某个环境ID。读取对象schema、已挂载能力和当前已发布指标定义，按函数名称、指标代码解析安装后的ID及版本。函数名不唯一、能力缺失或必填参数不全时，先说明缺口，不调用同名替代品。查询前核对实时输入schema；示例ID和数量不能作为默认业务参数。

这是只读业务分析Skill。只调用依赖清单允许的查询/分析能力，不执行退款、改价、调库存、采购创建、源表写入、数据库DDL、事件生成或消息发送。不恢复已移出的搜索、抓取、取时MCP或消息Skill。业务实体基于源表，不创建汇总视图实体。

统一人民币CNY，金额使用Decimal并按两位小数ROUND_HALF_UP展示；比率分母为0输出“无定义”，不能用0%代替。字段缺失、空值和真正的零值分别说明。时间使用Asia/Shanghai并明确起止、含不含边界和归属字段；不能擅自将库内无时区时间加8小时。相对窗口先确认分析基准日或as_of，固定样例不自动跟随机器当天漂移。

检查每次调用的HTTP状态、函数exit_code/stderr、业务complete/limited、分页与warnings。拿到截断或不完整结果时继续分页或明确仅为局部，不将部分和当全量。无数据不直接解释为零经营额；按指标no_data_policy区分。多个源表查询不构成事务快照，不与滞后索引结果强行合并。遇到源表/索引差异，列出证据和待重建事项，不擅自重建索引。

输出顺序：业务结论→范围/时间/口径→关键数值→对象ID与来源能力/版本→异常和不确定性→建议。不得输出凭据或无必要的姓名、电话、地址。建议不等于已经执行。

阅读 `references/workflows.md` 获取具体分支，`references/dependencies.json` 获取依赖契约，`queries/queries.json` 获取只读查询模板。只读取当前分支需要的材料。

## 使用边界

正例：订单应付和实际到账为什么不同？请核对指定订单收退款。；统计已完成退款和申请退款的差异，并解释净收款。；按我给出的高、中消费阈值分析这些用户。。

不使用：立即给客户执行退款。；查询SKU缺货依赖哪笔补货采购。。

## 执行方式：Skill编排，函数访问平台

本Skill沙箱没有平台认证上下文，禁止在包内脚本导入OSDK或发起平台请求，也不要求用户把凭据传入脚本。Agent先读取本Skill并确认业务范围，再从当前网络已挂载能力按名称解析业务组合函数 `ecommerce_finance_workflow` 的ID、工具箱及实际输入schema。调用方使用正常已授权的工具执行能力调用该函数；函数环境负责OSDK访问平台及复用底层查询。传入当前上下文kn_id与用户确认参数，不猜测ID、不固定环境。

解析执行响应：只有HTTP成功、函数exit_code=0且result.status为complete或partial时才能采用。result.calls记录底层证据，result.results为业务事实。缺参、权限失败、SDK错误、status异常时停止，不能编造零结果。partial必须保留不完整提示。当前入口支持的字段见references/dependencies.json及查询到的函数schema。

拿到result后按references/workflows.md解释口径；需要平台沙箱生成格式化说明时执行 `python scripts/render_v111.py --facts-file FACTS_JSON_PATH`，或把JSON作Base64编码后使用 `--facts-base64 ENCODED_FACTS`。这些参数只传业务事实，不传Token或账号密码。render_v111.py只处理输入事实，不能自行验证来源真实性，也不能替代授权查询。

平台执行顺序：读取Skill→调用业务组合函数→检查状态与证据→按Skill解释；可选离线渲染。不能直接启动旧版本要求kn_id的联网脚本。没有新增MCP、源表或视图实体。
