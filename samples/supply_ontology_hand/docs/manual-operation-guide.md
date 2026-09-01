# 人工操作手册：界面与脚本模式

人工模式由“界面操作 + 脚本操作”组成，不通过 Agent 对话完成业务判断。

## 第 1 步：人工导入数据库表（必做）

数据库表导入是线上体验的前置环节，必须由操作者使用数据库连接信息完成，不能只在 OpenBKN 界面导入 KN JSON。执行：

```bash
cp tools/config.example.yaml tools/config.yaml
```

随后按本环境填写 `tools/config.yaml` 的 `database.*` 和 `vega.catalog_name`；密码只能留在本机，不能提交。

```bash
python3 tools/load_sample_data.py --interactive --create-database --table-prefix hand_
```

提示：数据库名与 OpenBKN Catalog 名称由本环境操作者分别创建并记录，例如 `<sample_database>` 与 `<sample_catalog_name>`。两者不同，Catalog ID 也不能当数据库名输入；不要复用其他 POC、客户或报告中的名称和 ID。

依次输入 PostgreSQL Host、端口、数据库名、用户名和密码。连接测试成功后输入 `yes`，脚本会创建 `hand_` 前缀表并保留原有业务表。

## 界面操作（手工路径）

1. 登录 OpenBKN 控制台。
2. 进入“领域知识网络 → 知识网络管理”。
3. 使用“导入”上传 `kn/supply_ontology_hand.json`。
4. 检查知识网络名称、对象类、关系类、指标和行动类数量。
5. 在数据资源/绑定页面选择对应资源并完成对象类绑定。
6. 在验证页面确认知识网络可查询，再进入脚本验证。

## 脚本操作（Agent/CLI 路径；不要与上面的 UI 导入重复执行）

```bash
cd tools
python3 load_sample_data.py --config config.yaml
python3 import_kn.py --json ../kn/supply_ontology_hand.json --resolve-embedding
python3 setup_catalog.py --config config.yaml --write-config
python3 bind_kn_resources.py --config config.yaml --dry-run --table-prefix hand_
python3 bind_kn_resources.py --config config.yaml --table-prefix hand_
python3 verify_sample.py
```

再完成 Skill、指标和 Action 数据集。所有支持 dry-run 的写入先预检；KN 导入、Skill 注册和数据库 DDL 没有平台 dry-run 时，必须先确认目标环境与名称。

```bash
python3 register_skills.py
python3 register_skills.py --apply
python3 setup_skill_dataset.py --interactive --apply --kn-id supply_ontology_hand
python3 setup_catalog.py --config config.yaml --write-config
python3 bind_skill_dataset.py --kn-id supply_ontology_hand --catalog-id <catalog-id-from-config.yaml> --apply
python3 power_layer.py --dry-run all --kn-id supply_ontology_hand
python3 power_layer.py all --kn-id supply_ontology_hand
```

默认函数使用 OpenBKN 原生 Function Runtime；在确认 Toolbox 名称后可重复执行：

```bash
python3 register_native_function_toolbox.py --apply
```

### 原生函数工具箱

Toolbox 名称只能使用中文、字母、数字和下划线，不能含连字符、空格或其他标点。创建前先在 UI 或 `openbkn toolbox list` 中确认同名 Toolbox；如果 POC 返回连接超时，先检查 `openbkn auth status` 和 Toolbox 列表，再决定是否重试，避免重复创建。

默认样例使用 OpenBKN 内建的 `metadata_type=function` 运行时，不需要函数服务器地址、Docker、`host.docker.internal` 或独立函数服务。操作者只需已登录 OpenBKN；脚本会创建或更新 `供应链原生计算函数` Toolbox，并发布按业务命名的函数。调用者只传业务参数；函数在受控运行时读取已绑定的知识网络。

### Action Dataset 建表

Agent 模式可用以下命令一次完成幂等建表、三张表验收和对象类绑定；密码只在提示时输入，不写入配置：

```bash
python3 bootstrap_action_layer.py \
  --config config.yaml \
  --interactive --apply
```

若采用纯手工模式，仍可直接执行 `datasets/postgres/001_action_datasets.sql`；执行前确认目标库，执行后核对 `sc_pr_decision`、`sc_plan_monitor_task`、`sc_plan_monitor_item`。

人工模式的界面截图、资源 ID 和操作时间应记录在本次验证报告中；不得把环境特定 ID 写回可移植 KN JSON。

## 供应承诺问题

使用 `docs/qa-eval-set.yaml` 中的未来预测案例，记录查询结果、计算证据和最终结论。
