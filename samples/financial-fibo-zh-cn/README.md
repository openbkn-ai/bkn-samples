# 金融投资组合运营（FIBO 参考，中文）

以虚构资产管理机构的证券交易后控制为场景，从金融工具、法律实体和组合，追溯到成交、结算、持仓、价格、估值、发行方集中度和未结算应收限额。适用于本地建模、数据关联和业务问答验证。

## 从哪里开始

1. [业务 PRD](docs/PRD.md)：业务角色、关切、P0 决策和业务边界。
2. [本体规范与计算口径](docs/bkn-modeling-spec.md)：20 类对象、29 条关系、3 个分组及所有财务公式。
3. [FIBO 语义映射](docs/fibo-operational-mapping.md)：来源、固定修订、映射方式和明确扩展。
4. [数据设计与业务分支](docs/dataset-scenarios.md)：表记录数、关联方式和共享价格的传播影响。
5. [100 题与完整答案](bkn-eval/answers.md)：10 个验收场景；简单 30 题、中等 40 题、复杂 30 题。

当前观察日为 **2027-02-28**；2026-11 至 2027-02 是实际视图，2027-03-31 为从观察日预测的计划视图。全部事实使用日期。每表至少 50 条，最大表超过 16,000 条；本轮合计 **78,356 条/语言**。中文业务名称、状态、原因、题目和答案均中文表达；业务 ID、币种、字段和官方来源标签保留稳定编码。

## 本地验证

在本目录执行，Python 3.9+，仅标准库；不下载数据或依赖、不需要平台凭据：

```bash
openbkn bkn validate kn
python3 tools/verify.py
python3 bkn-eval/run.py
```

原生 BKN 校验需要预装 OpenBKN CLI。脚本逐一重算 8,000 个持仓、8,000 个估值、5,000 项限额评估，并回放锁定的 100 题答案。仓库根目录额外执行 `python3 tools/financial_fibo/test_financial_fibo.py` 可验证双语等价、负向注入和回归控制。

`data/` 是锁定 CSV，`dataset.lock` 保存摘要与行数；`kn/network.bkn` 是唯一模型入口；`model-contract.json` 记录字段和关系映射；`bkn-eval/` 包含题目、完整结构化答案、只读证据 SQL 与回放器。源码目录的 `verification/` 保存本地验证结果，不随安装包交付。

## 评审记录

[首轮问题、修复与独立复验](docs/expert-review-resolution.zh-CN.md)记录本轮55项控制与完整评审证据。

## 来源与交付边界

来源为 [EDM Council FIBO 官方仓库](https://github.com/edmcouncil/fibo)，固定修订 `2d73435a4419b66b7c9f44cb9763e35fe8ac7890`，MIT 许可。六份原始 RDF、原许可、SHA-256 和具名类/属性清单保存在 [fibo-reference/](fibo-reference/README.md)。本包只使用已声明业务范围对应的来源模块，未声明覆盖整个 FIBO 或其完整导入闭包。

本样例是本地离线候选包，要求 **OpenBKN >=0.2.1 <0.3.0**。[离线安装说明](docs/offline-installation.md)采用 Studio 标准导入、安装流程和共享 MariaDB。包内包含 `sample.yaml`、带类型的数据加载与完整核验脚本、原生 BKN 导入与数据源绑定脚本。未创建官方目录条目或线上发布。SQL 回放用于校验冻结答案，不能代表模型准确率；实际仅题目输入的模型问答记录与评分作为独立验收产物保存。估值快照与 SQL 是样例数据和离线验收工具，不安装运行时指标、函数或 Skill。
