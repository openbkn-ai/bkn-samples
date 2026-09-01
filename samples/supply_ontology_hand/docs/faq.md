# FAQ：第三方导入与 Embedding 模型绑定

## Q1：为什么导入时提示模型获取失败？

最常见原因是 `index_config.vector_config.model_id` 来自另一个环境。模型 ID 是平台实例内的资源 ID，不保证跨环境或跨租户有效。本 sample 已在 POC 实际复现过该问题。

## Q2：第三方用户怎么检查当前环境的 embedding？

Agent 模式先完成 OAuth 登录，再执行：

```bash
openbkn --json model small list
openbkn --json model small get-default --type embedding
```

确认 `model_type` 为 `embedding`，使用返回的 `model_id`。不要复制其他环境、旧报告或他人 JSON 中的 ID。

## Q3：怎么修复 JSON？

把所有启用向量索引属性的 `vector_config.model_id` 替换为目标环境可用的 embedding ID，保持 `vector_config.enabled` 不变。Agent 模式可直接让导入脚本动态读取目标环境默认 embedding：

```bash
python3 tools/import_kn.py --json kn/supply_ontology_hand.json --resolve-embedding
```

## Q4：如何不写平台先验证？

```bash
python3 tools/import_kn.py --json kn/supply_ontology_hand.json --dry-run
```

dry-run 只能验证本地 JSON 和请求准备，不能证明目标环境的模型 ID 有效；仍需做一次目标环境 API 导入或平台 schema 校验。

## Q5：导入后如何确认 embedding 真可用？

先执行 `openbkn --json bkn get <kn_id> --stats`，再对启用向量索引的字段执行一次语义搜索，并记录结果、模型 ID 和时间。知识网络创建成功不等于异步索引已经完成。

## Q6：为什么导入后指标数量可能是 0？

知识网络导入与指标注册是两个能力。`metrics_total: 0` 表示当前环境尚未注册指标，不代表对象类或关系导入失败。注册指标后用以下命令核验：

```bash
openbkn --json bkn metric list <kn_id>
```

函数与 Skill 也必须分别验收，不能用 KN 导入成功替代完整交付验收。

## Q7：手工模式怎么处理？

在 UI 的模型/索引配置中选择当前环境可用的 embedding，再导入 JSON。原则与 Agent 模式相同：不能照抄其他环境的 model ID。

## Q8：为什么 Toolbox 创建提示名称格式错误？

POC 的 Toolbox 名称只允许中文、英文字母、数字和下划线。不要使用连字符、空格或括号，例如使用 `供应链计算函数工具箱P0`。

## Q9：POC API 连接超时后能不能直接重试创建？

不能直接盲目重试。先执行 `openbkn auth status`，再执行 `openbkn toolbox list --limit 100` 确认同名 Toolbox 是否已经创建。

## Q10：函数 Toolbox 创建成功但调用失败怎么办？

先确认是否使用默认的原生 Function Toolbox：执行 `python3 tools/register_native_function_toolbox.py --apply`。该路径不需要 `FUNCTION_SERVICE_URL`；函数由 OpenBKN 内建运行时执行。

函数只接收业务参数，不传 BOM/库存快照、`resolved_context`、Token 或服务地址。先用 MCP 的 `list_published_toolboxes` / `list_published_tools` 发现“供应链原生计算函数”和目标函数；再在新的受管 Interaction 中调用 `execute_published_tool`。若函数内部读取知识网络失败，记录平台返回的错误和 Interaction ID，由环境管理员检查调用者对知识网络的查询权限；不要改用 CSV 或本地计算冒充线上结果。

## Q11：为什么网页/内置 Agent 查询不到本环境数据，但 CLI 能查到？

先不要判断数据导入失败。必须先回读当前 Agent 实际使用的 `kn_id`、Catalog 和对象类 `data_source`。可复现的只读验证入口是已认证的 `openbkn context` CLI；如果内置连接器返回公共或旧 Resource，说明环境路由不一致，应停止业务验收并切换到当前环境的 Context Loader。不能用其他环境资源的查询结果替代本环境证据。

验证命令示例：

```bash
openbkn --json context tool-call supply_ontology_hand bkn_start_interaction \\
  --args '{"agent_name":"<your_agent_name>","question":"请验证产品 U00-000080 的预测证据。"}'
```

后续查询必须复用返回的 `conversation_id` 和 `interaction_id`，并在结束时调用 `bkn_finish_interaction`。

## Q12：数据库名和 OpenBKN 连接名称是不是一回事？

不是。由部署者为本环境分别创建 PostgreSQL 数据库（如 `<sample_database>`）与 OpenBKN 物理 Catalog（如 `<sample_catalog_name>`）；Catalog ID 由平台创建后返回。数据库脚本提示数据库名时只能填数据库名，不能填 Catalog 名称或 Catalog ID。不要复制其他 POC、客户或报告中的这些值。
