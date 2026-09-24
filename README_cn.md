# BKN Samples

[English](./README.md)

OpenBKN 官方体验样例集合：知识网络模型、样例数据与分步导入工具。

## 一键安装

使用 OpenBKN 管理员账号登录后，在仓库 checkout 中执行：

```bash
./install.sh list
./install.sh supply-chain --runtime k8s
./install.sh world-cup --runtime k8s
```

在 OpenBKN 集群外运行 Docker 时，传入 Vega 能访问的数据库主机地址。安装器为供应链和世界杯分别使用默认端口 `13306`、`13307`：

```bash
./install.sh supply-chain --runtime docker --catalog-host 10.0.0.8
```

本机未登录时，交互模式会引导 `openbkn auth login <url> --device`；非交互模式只输出准确登录命令并停止。使用 `--dry-run` 可以只查看计划、不产生写入。

安装器要求 `openbkn vega catalog create`、`update` 和 `test-connection-config` 均支持 `--connector-config-file`。它不会回退到把数据库密码写入命令行 JSON 的方式。

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
