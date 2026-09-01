# 伙伴执行手册：供应链手工体验包

这是唯一操作入口。完成步骤 1～7 后，第三方 Agent 可通过 MCP 演示供应链问题，并可运行核心 50 题 A/B/C 对比评测。

## 开始前

| 谁负责 | 必须确认 |
|---|---|
| 平台管理员 | OpenBKN 可登录；账号可导入 KN、管理 Catalog、发布函数和 Skill；平台可访问目标数据库。 |
| DBA / 伙伴 | 已创建专用体验库；账号具备建表、删表、写入权限。不要使用生产库。 |
| 执行人 | Python 3.11+、Node.js `>=24.19.0`、`@openbkn/bkn-sdk@0.1.4`。 |

```bash
nvm use 24.19.0
npm install -g @openbkn/bkn-sdk@0.1.4
openbkn auth login <platform-url>
```

## 步骤 1：配置与前置检查

```bash
cd tools
cp config.example.yaml config.yaml
# 编辑 database 的 engine/host/port/database/user/password；必要时填 vega.catalog_host
python3 -m pip install -r requirements.txt
python3 preflight.py --config config.yaml
```

`preflight` 只检查本机 CLI、Node 和配置，不访问平台或数据库。PostgreSQL 用 `engine: postgres`，MySQL 用 `engine: mysql`；MySQL 不要配置 `vega.connector_options.sslmode`。

## 步骤 2：灌入样例数据

```bash
python3 load_sample_data.py --config config.yaml
```

成功标志：输出 12 张表及行数。此步骤会重建同名体验表；库名或目标不确定时停止并联系 DBA。

## 步骤 3：导入知识网络

```bash
python3 import_kn.py --resolve-embedding
openbkn --json bkn get supply_ontology_hand
```

成功标志：返回 ID `supply_ontology_hand` 和名称“供应链本体知识网络-手工版”。若返回 `BindBusinessDomainFailed`，先用 `bkn get` 确认是否部分创建；未创建则由平台管理员检查 business-system 网络、DNS 和 TLS。

## 步骤 4：创建 Catalog 并扫描

```bash
python3 setup_catalog.py --config config.yaml --write-config
```

脚本会创建或复用 Catalog、测试连接、触发扫描并轮询资源。成功标志：`verification.ok: true`、`found_count: 12`，且 `config.yaml` 已写入 `vega.catalog_id`。

## 步骤 5：绑定并冒烟

```bash
python3 bind_kn_resources.py --config config.yaml --dry-run
python3 bind_kn_resources.py --config config.yaml
python3 smoke_test.py --config config.yaml
```

成功标志：dry-run 为每个绑定对象解析到 resource ID，冒烟检查通过。监控任务对象初始为空属预期。

## 步骤 6：业务能力与 MCP 验收

```bash
python3 power_layer.py all --kn-id supply_ontology_hand
python3 register_native_function_toolbox.py --apply
python3 register_skills.py --apply
```

原生函数实现位于 `tools/fn/`，由 OpenBKN 内建运行时发布为原生 Function Toolbox。第三方 Agent 仅通过 OpenBKN MCP 证明三件事：能发现已发布工具箱与 Skill；能以业务参数调用“标准交期”和“BOM清单”；能分别演示可售、净需求/多需求覆盖和指定交期履约。保留 Interaction 与结果作为验收证据。函数不得接收 Token、服务地址、快照或 `resolved_context`；不得用 CSV、CLI 或 SQL 冒充 MCP 调用结果。

## 步骤 7：核心 50 题系统评测对比

进入包内 [BKN-Eval](../bkn-eval/README.md)，按[体验评测指南](../bkn-eval/体验评测指南.md)完成：

1. A：基于知识网络和 MCP 答题；
2. B：只读同一数据快照的数据库答题；
3. C：在 A/B 回答冻结后，使用金标独立评判并输出对比报告。

本版本只运行核心 50 题。每次平台、题集、答案集、模型或函数版本变化后，都应新建一份报告，不覆盖历史结果。

## 失败分流

| 现象 | 处理人 / 下一步 |
|---|---|
| CLI/Node 版本不通过 | 执行人按 preflight 提示切换到 0.1.4 / 24.19.0。 |
| MySQL `sslmode` 错误 | 删除该配置；脚本会忽略旧字段。 |
| Catalog 连不上库 | DBA / 平台管理员核对平台到数据库的网络、账号和 `catalog_host`。 |
| 绑定找不到表 | 先确认扫描资源已有 12 张表；仍失败再由实施人员在控制台手绑。 |
| Agent 发现不到函数或 Skill | 平台管理员核对步骤 6 的发布状态与 Agent 的 MCP 读取权限。 |

所有样例数据均为脱敏历史回放，不代表实时库存或真实交期；不要演示自动下采购订单。
