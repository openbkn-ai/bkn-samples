# BKN Samples

[English](README.md)

OpenBKN 官方样例集合，提供知识网络模型、数据、对象关系和业务场景。通过**一键体验**安装样例，再让外部 Agent 通过 MCP 查询和分析已发布的本体。

每个样例都是独立交付包，拥有自己的数据库、知识网络和发布版本。函数、指标和 Skill 按样例实际声明提供。

## 开始体验

准备已启用标准样例安装服务的 OpenBKN 0.2.x 环境，并使用具备样例安装权限的账号。制造业、金融 FIBO 及零售 GS1 样例要求 **OpenBKN 0.2.1 及以上**，当前清单兼容范围为 `>=0.2.1 <0.3.0`。

1. 打开 **Studio → 一键体验**，点击**刷新样例**。
2. 选择已发布的样例，查看版本与更新说明，点击**安装**。
3. 等待安装和验证完成，打开对应知识网络。
4. 接入外部 Agent，通过 MCP 查看模型、查询对象数据，并按需使用样例声明的函数、指标或 Skill。
5. 体验结束后点击**卸载**。安装历史会保留，清理完成后可以重新安装。

离线候选包通过**导入离线包**上传固定的 `.tar.gz` 文件；若包声明了数据镜像，该镜像也必须在目标集群可用。FIBO 包使用产品提供的共享 MariaDB，无需单独的样例数据库镜像。使用 Studio 标准安装流程不要求用户自行配置 CLI 和 Python，这些工具用于样例开发。

## 样例目录

OpenBKN 0.2.1 提供 **12 个标准样例**：供应链、世界杯、制造业、金融 FIBO、零售 GS1、能源 SAREF4ENER 各中英文一对，全部登记在 [0.2.1 目录](catalogs/0.2.1/catalog.json)。订单入门不在 0.2.1 提供，保留原有版本。0.2.1 的每个 Release 标题以 `[OpenBKN 0.2.1]` 开头。

| 样例 | 语言 | 场景 | 可用版本 |
| --- | --- | --- | --- |
| [Order Basics](samples/order-basics/) | 中文 | A small starting point for orders, products and object relationships | 原始 020： 0.1.2；0.2.1 不提供 |
| [Supply Chain](samples/supply_ontology_hand/) | 中文 | PMC 生产计划与采购：欠货、可做与可承诺数量、缺料与跟进 | 原始 020： [0.1.16](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-v0.1.16)；0.2.1： [0.1.18](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-v0.1.18) |
| [Supply Chain](samples/supply_ontology_en/) | 英文 | 英文版 PMC 与采购场景 | 原始 020： [0.1.1](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-en-v0.1.1)；0.2.1： [0.1.13](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-supply-chain-en-v0.1.13) |
| [World Cup](samples/world-cup/) | 中文模型、英文数据 | 赛事、球队、球员和比赛事件 | 原始 020： 0.1.2；0.2.1： [0.1.8](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-world-cup-v0.1.8) |
| [World Cup](samples/world-cup-en/) | 英文 | 赛事、球队、球员和比赛事件 | 原始 020： 0.1.0；0.2.1： [0.1.4](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-world-cup-en-v0.1.4) |
| [Manufacturing Operations](samples/manufacturing-industry-en-us/) | 英文 | 精密加工订单履约：交付、物料、执行合规、质量放行、采购与维护 | 0.2.1：[0.1.6](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-manufacturing-industry-en-us-v0.1.6) |
| [制造业端到端运营](samples/manufacturing-industry-zh-cn/) | 中文 | 精密加工订单履约：交付、物料、执行合规、质量放行、采购与维护 | 0.2.1：[0.1.6](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-manufacturing-industry-zh-cn-v0.1.6) |
| [Financial Portfolio Operations (FIBO)](samples/financial-fibo-en-us/) | 英文 | 交易后运营、估值、集中度与限额 | 0.2.1：[0.2.8](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-en-us-v0.2.8) |
| [金融投资组合运营（FIBO）](samples/financial-fibo-zh-cn/) | 中文 | 交易后运营、估值、集中度与限额 | 0.2.1：[0.2.8](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-financial-fibo-zh-cn-v0.2.8) |
| [Food Supply and Recall (GS1)](samples/retail-gs1-en-us/) | 英文 | 到货质检、批次追溯、仓库与门店履约、补货和召回 | 0.2.1：[0.1.3](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-en-us-v0.1.3) |
| [食品供应链追溯与召回（GS1）](samples/retail-gs1-zh-cn/) | 中文 | 到货质检、批次追溯、仓库与门店履约、补货和召回 | 0.2.1：[0.1.3](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-retail-gs1-zh-cn-v0.1.3) |
| [Energy demand response (SAREF4ENER)](samples/energy-saref4ener-en-us/) | 英文 | 可承诺容量、同时段调度、交付核实与结算 | 0.2.1：[0.1.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-energy-saref4ener-en-us-v0.1.7) |
| [需求响应与柔性用能（SAREF4ENER）](samples/energy-saref4ener-zh-cn/) | 中文 | 可承诺容量、同时段调度、交付核实与结算 | 0.2.1：[0.1.7](https://github.com/openbkn-ai/bkn-samples/releases/tag/sample-energy-saref4ener-zh-cn-v0.1.7) |

0.2.1 的每个样例都按业务角色重整：有业务 PRD、50 题业务场景测试集（参考答案独立计算）、按角色编写的 Skill 和 15 张体验卡；去掉指标，只为 Cypher 表达不了的计算保留函数，社区版即可完整使用。每个 Release 都在 OpenBKN 0.2.1 主线构建（arm64）上全新安装，通过 API 核验了参考 Cypher 查询、图模式、声明的原生函数及挂载 Skill；未执行完整问答卡、浏览器 UI 或模型问答评分。验收证据与边界记录在各自的 `verification.json` 和 `online-acceptance.json`。

已发布 0.2.0 客户端继续使用根[官方目录](catalog.json)。更新后的样例服务按产品版本选择目录，见 [0.2.0 目录](catalogs/0.2.0/catalog.json)、[0.2.1 目录](catalogs/0.2.1/catalog.json)和[目录选择说明](docs/product-version-catalogs.md)。每个 0.2.1 样例只保留当前通过验收的 Release。已删除本轮替代的 12 个旧 Release 及附件，也删除了失败的英文供应链 0.1.12 草稿。旧目录条目仅以撤回状态保留，供既有安装历史识别；源码保留在 Git 历史中。0.2.0 Release 不受影响。详见[清理记录](docs/release-cleanup-021-20261031.md)。

世界杯数据是冻结的历史快照，包含截至 2022 年的男足赛事和截至 2019 年的女足赛事。各样例的数据范围、许可和场景假设见对应 README。

## 场景评测

每个样例在 `bkn-eval/baselines/` 下维护业务场景测试集：按 PRD 场景编写的问题集（基础 12、中等 20、复杂 18）、不向被测方提供的答案集、从交付数据计算答案的脚本，以及外部 MCP 智能体的运行记录。

由独立的外部 Agent 通过 MCP 解答问题，评测过程中不提供参考答案，完成后核对业务值。每次评测记录实际使用的样例包和测试结果。

## 开发与发布

新增或更新样例请先阅读[样例开发指南](docs/SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md)。本地开发需要与平台版本兼容的 [openbkn CLI](https://github.com/openbkn-ai/bkn-sdk)、Python 3.11+，以及样例脚本声明的依赖。

```text
samples/<directory>/
├── sample.yaml                 # 样例身份、组件与安装 hooks
├── README.md                   # 使用方式、场景与数据范围
├── dataset.lock                # 数据来源与摘要，按数据模式提供
├── data/                       # 内嵌样例数据
├── kn/                         # BKN 模型或 KN JSON
├── db/                         # 数据库初始化与验证
├── platform/                   # 标准托管安装与验证 hooks
├── tools/                      # 声明的函数或开发辅助工具
├── skills/                     # 声明的业务 Skill
├── bkn-eval/                   # 问题集、参考答案与基线校验，按需提供
└── releases/<version>/         # 版本说明与正式制品元数据
```

新增样例通过 manifest 和标准 hooks 接入，并更新上方样例目录；安装器动态发现样例身份。面向用户的样例内容统一使用目标语言，只声明实际安装的组件。验收同一份固定样例包及其实际运行依赖，发布不可覆盖的制品及元数据后，再把版本注册到对应产品版本的目录。

评测集和测试保留在源码仓库；执行日志、临时绑定、翻译映射及本地过程文件不进入发布包。

相关指南：

- [开发与版本更新](docs/SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md)
- [固定包构建与发布](docs/candidate-publication.md)
- [卸载与重装](docs/sample-uninstall.md)
- [样例服务部署](docs/sample-service-deployment.md)
- [设计与文档索引](docs/README.md)

[供应链缺料规则 #190](docs/shortage-rule-190.md)：已停用，供应链 0.1.17 与英文版 0.1.11 不再发布。

0.2.1 正式发布清单、撤回的旧版本和删除的 Release 见 [0.2.1 发布记录](docs/release-0.2.1-20261031.md)；更早的保留计划见[版本保留与转正计划](docs/release-retention-20261030.md)。
