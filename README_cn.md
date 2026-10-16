# BKN Samples

[English](README.md)

OpenBKN 官方样例集合，提供知识网络模型、数据、对象关系和业务场景。通过**一键体验**安装样例，再让外部 Agent 通过 MCP 查询和分析已发布的本体。

每个样例都是独立交付包，拥有自己的数据库、知识网络和发布版本。函数、指标和 Skill 按样例实际声明提供。

## 开始体验

准备已启用标准样例安装服务的 OpenBKN 0.2.x 环境，并使用具备样例安装权限的账号。制造业离线包要求 **OpenBKN 0.2.1 或更高版本**。

1. 打开 **Studio → 一键体验**，点击**刷新样例**。
2. 选择已发布的样例，查看版本与更新说明，点击**安装**。
3. 等待安装和验证完成，打开对应知识网络。
4. 接入外部 Agent，通过 MCP 查看模型、查询对象数据，并按需使用样例声明的函数、指标或 Skill。
5. 体验结束后点击**卸载**。安装历史会保留，清理完成后可以重新安装。

离线候选包通过**导入离线包**上传固定的 `.tar.gz` 文件；包引用的数据镜像也必须在目标集群可用。使用 Studio 标准安装流程不要求用户自行配置 CLI 和 Python，这些工具用于样例开发。

## 样例目录

| 样例 | 语言 | 体验场景 | 可用状态 |
| --- | --- | --- | --- |
| [订单入门](samples/order-basics/) | 中文 | 用少量订单和产品了解对象及关系 | 在线目录已发布 |
| [供应链](samples/supply_ontology_hand/) | 中文 | 订单、预测、BOM、库存、采购、缺料及交付分析 | 在线目录已发布 |
| [供应链](samples/supply_ontology_en/) | 英文 | 英文数据、本体、函数、指标和 Skill 的供应链分析 | 在线目录已发布 |
| [世界杯](samples/world-cup/) | 中文模型、英文数据 | 赛事、球队、球员和比赛事件查询，提供 50 道中文评测题 | 在线目录已发布 |
| [世界杯](samples/world-cup-en/) | 英文 | 对象查询、多表关联、排名及跨届赛事分析，提供 50 道评测题 | 源码已合并，在线发布待完成 |
| [Manufacturing Operations](samples/manufacturing-industry-en-us/) | 英文 | 从预测到发运的制造履约，含 40 张表、71 条关系和 100 道中英对照评测题 | 仅离线发布；要求 OpenBKN ≥ 0.2.1 |
| [制造业端到端运营](samples/manufacturing-industry-zh-cn/) | 中文 | 从预测到发运的制造履约，含 40 张表、71 条关系和 100 道中英对照评测题 | 仅离线发布；要求 OpenBKN ≥ 0.2.1 |

可下载版本以[官方目录](catalog.json)为准。源码合并不等于在线包发布：英文世界杯已完成源码合并与本地安装验收，正式镜像、发布包和目录注册仍需完成独立发布流程。

两个制造业样例刻意不加入官方目录和历史 `020` 发现入口。请在目标集群预先加载与离线包匹配的数据镜像，再导入固定离线包；它们使用独立数据库和知识网络 ID，可并存安装。

世界杯数据是冻结的历史快照，包含截至 2022 年的男足赛事和截至 2019 年的女足赛事；不同明细表的覆盖范围有所差异。各样例的数据范围、许可和场景假设见对应 README。

## 场景评测

提供评测集的样例在 `bkn-eval/` 中维护问题集、参考答案与基线校验：

- [供应链评测](samples/supply_ontology_hand/bkn-eval/README.md)
- [英文供应链评测](samples/supply_ontology_en/bkn-eval/README.md)
- [世界杯评测](samples/world-cup/bkn-eval/README.md)：50 道中文题，明确输出字段和排序，提供冻结参考答案与评分脚本。
- [英文世界杯评测](samples/world-cup-en/bkn-eval/README.md)：基础查询统计 10 题、多表关联 12 题、排名和跨届对比 14 题、综合分析 14 题。

由独立的外部 Agent 通过 MCP 解答问题，评测过程中不提供参考答案，再核对业务值、输出字段及排序。每次评测记录实际使用的数据基线、样例包和测试结果。

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

新增样例通过 manifest 和标准 hooks 接入，并更新上方样例目录；安装器动态发现样例身份。面向用户的样例内容统一使用目标语言，只声明实际安装的组件。验收同一份固定样例包和数据镜像，发布不可覆盖的制品及元数据后，再把版本注册到 `catalog.json`。

评测集和测试保留在源码仓库；执行日志、临时绑定、翻译映射及本地过程文件不进入发布包。

相关指南：

- [开发与版本更新](docs/SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md)
- [固定包构建与发布](docs/candidate-publication.md)
- [卸载与重装](docs/sample-uninstall.md)
- [样例服务部署](docs/sample-service-deployment.md)
- [设计与文档索引](docs/README.md)
