# 世界杯

用 Joshua C. Fjelstul 公开的世界杯历史数据，查询赛事、球队、球员、比赛和进球、红黄牌、换人、点球大战等事件。包含 27 张数据表、本体和 1 个业务 Skill。业务需求与口径见 [PRD](docs/PRD.md)。

[English documentation](README.md)

## 安装与体验

1. 登录 OpenBKN，进入首页的**一键体验**。
2. 刷新官方目录，选择**世界杯**并点击**安装**，要求 **OpenBKN >=0.2.1 <0.3.0**。
3. 等待安装和验证完成，打开世界杯知识网络。
4. 在智能问答、数据查询和图探索页面试用体验卡，或接入外部 Agent，通过 MCP 查询对象和使用 Skill。

无法访问官方目录时，从 [Releases](https://github.com/openbkn-ai/bkn-samples/releases) 下载本样例的 `package.tar.gz`，在一键体验中选择**导入离线包**后安装。

冻结快照包含 **27 张 CSV 表、81,200 行**：截至 2022 年的 22 届男足世界杯和截至 2019 年的 8 届女足世界杯。各类明细覆盖的届次不同；人名、球队和奖项名称保留数据源英文原文。

## 能力

全部问题都能用 Cypher 查到，样例不提供函数，也不使用指标，社区版即可完整使用。

- **Cypher 查询**：赛事与主办国、球队与足联、大名单与球员、教练与裁判、球场、比赛与比分、进球、红黄牌、换人、点球大战、积分榜与最终名次、奖项。
- **Skill**：“世界杯历史分析”，面向体育编辑、球队分析师和赛事数据管理员，写明业务口径、Cypher 写法和回答格式。

## 体验卡

15 张体验卡从测试集中选题，覆盖届数、2022 年概况、决赛与点球大战、进球与红黄牌、梅西的奖项和进球、联合举办、1950 年赛制和两位穆勒对比。卡片的数据查询和图探索 Cypher 用 `tools/acceptance/experience_set.py` 在安装后的平台上在线核验。

## 验收与维护

测试集见 [业务场景测试集 v1](bkn-eval/baselines/2026-10-31-business-scenarios-v1/README.md)，参考答案由参考 SQL 直接从锁定的 CSV 计算，不随安装包交付。安装后让未读答案的智能体每题跑一轮；未达 100% 时记录失败原因，先改本体描述或 Skill，不改题目和答案迁就结果。

安装 hooks 在内部调用 `run.sh` 并注册 Skill；用户使用一键体验或离线包导入，无需手工执行脚本。修改数据或模型后，按[样例开发指南](../../docs/SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md)构建固定候选并完成验收后再发布新版本。升级时先卸载旧样例，再安装新版本。

## 数据来源与许可

数据来自 [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup)，固定提交为 `35a8667f518b07469182ae16d35574dd0e7a00fb`；27 个 CSV 文件的摘要见 [dataset.lock](dataset.lock)。

© 2023 Joshua C. Fjelstul, Ph.D. 数据采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可，分享数据或衍生数据时保留署名和相同方式共享要求。
