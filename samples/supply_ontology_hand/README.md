# 供应链本体 · 手工体验包

这是一个脱敏、静态的供应链体验样例，用于演示产品、订单、库存、齐套和交期风险的可解释业务结论。

它不使用客户生产数据，也不会自动创建采购订单或写入 ERP。真实写回须另行配置工具、权限和审批。

## 获取最新发布版

新使用者直接拉取已验证发布版：

```bash
git clone --branch supply-ontology-hand-v0.1.4 --depth 1 https://github.com/openbkn-ai/bkn-samples.git
cd bkn-samples/samples/supply_ontology_hand
```

已有仓库先进入 `bkn-samples` 根目录再更新 tag：

```bash
git fetch origin --tags --force
git checkout --detach supply-ontology-hand-v0.1.4
cd samples/supply_ontology_hand
```

## 给客户

完成交付后，第三方 Agent 可经 MCP 回答：

- `382-000005` 有多少销售订单；
- 该产品在三个成品仓的可用库存；
- 指定日期能否交付、缺什么、为什么有风险。

样例是历史回放，不能用于真实交付承诺。

## 给实施伙伴

使用唯一入口：[伙伴执行手册](docs/openbkn-hand-import-guide_cn.md)。交付完成标准为：

1. 数据、本体和对象绑定完成；
2. 指标、业务函数与 S1/S2/S3 Skill 已发布；
3. Agent 经 MCP 抽样验收通过；
4. 步骤 7：包内 [BKN-Eval](bkn-eval/README.md) 完成核心 50 题 A/B/C 对比。

开始前需要可登录的 OpenBKN、专用 PostgreSQL/MySQL 体验库、可管理 Catalog 的账号，以及平台到数据库的网络连通性。不要把体验脚本指向生产库。

## 关键资产

- KN：`kn/supply_ontology_hand.json`
- 样例数据：`data/`（12 张 CSV）
- 配置模板：`tools/config.example.yaml`
- 导入与验收脚本：`tools/`
- 评测包：`bkn-eval/`

本包按 `@openbkn/bkn-sdk@0.1.4`、Node.js `>=24.19.0` 验证。
