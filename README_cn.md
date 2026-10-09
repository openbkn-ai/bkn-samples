# BKN Samples

[English](./README.md)

OpenBKN 官方体验样例集合：知识网络模型、样例数据与分步导入工具。

## 前置条件

- [OpenBKN 平台安装（飞书文档）](https://openbkn-ai.feishu.cn/wiki/Hby4wPzuhiFqD8klgMdcwvpBnde)
- [openbkn CLI（bkn-sdk）](https://github.com/openbkn-ai/bkn-sdk)
- Python 3.11+（运行 sample 内 `tools/` 脚本）

## Samples

| Sample | KN ID | 说明 |
|--------|-------|------|
| [supply_ontology_hand](samples/supply_ontology_hand/) | `supply_ontology_hand` | 供应链本体手工体验：CSV 灌库 → Catalog 扫描 → 对象类绑定 → Agent 场景体验 |
| [world-cup](samples/world-cup/) | `worldcup_vega_catalog_bkn` | 27 份公开世界杯 CSV（CC-BY-SA）→ MySQL → Vega Catalog → BKN 推送与索引构建 → 发布 `vega_sql_execute` 工具。单脚本 `./run.sh`，六步幂等 |

> 更多 sample 将陆续加入（如 `supply-chain-skill`）。

## 目录结构

每个 sample 均为**自包含交付包**：

```
samples/<slug>/
├── README.md              # English（默认）
├── README_cn.md           # 中文
├── kn/
├── data/
├── tools/
└── docs/
    ├── openbkn-hand-import-guide.md
    ├── openbkn-hand-import-guide_cn.md
    ├── agent-scenario-kn-capability-design.md
    └── agent-scenario-kn-capability-design_cn.md
```

**文档命名：** 英文为 base 文件名；中文加 `_cn` 后缀（如 `openbkn-hand-import-guide_cn.md`）。

## 贡献

在 `samples/<slug>/` 下新增 sample，提供 README（中/英）、数据、工具、文档，并更新上表。

样例更新须遵循 [PR 审查规则](docs/review/sample-pr-review-rules_cn.md)，按 PR 模板说明变更与验证证据；正式发布须验收同一份固定候选制品。
