# 世界杯

使用公开世界杯历史数据体验中文本体的对象查询、多表关联、排名和跨届分析。通过标准一键体验安装样例，再由外部 Agent 经 MCP 读取对象数据并完成计算。

[English documentation](README.md)

## 数据与模型

冻结快照包含 **27 张 CSV 表、81,200 行**，涵盖截至 2022 年的 22 届男足世界杯和截至 2019 年的 8 届女足世界杯。各明细表覆盖范围不同；人名、球队名称和历史身份保留源数据的英文拼写。

- 样例 ID：`world-cup`
- 知识网络：`worldcup_vega_catalog_bkn`
- 数据库：`worldcup`
- 本体：27 个对象、29 条关系、4 个概念组
- [模型概览](bkn-network-structure.html)

## 一键体验

1. 打开 Studio 的**一键体验**，刷新样例目录。
2. 选择世界杯，查看版本说明，点击**安装**。
3. 等待安装与验证完成，打开世界杯知识网络。
4. 外部 Agent 通过 MCP 查看对象定义、分页查询实例，并自行关联和分析所需数据。
5. 使用**卸载**清理样例；清理完成后可以重装，安装历史保留。

无法访问官方目录时，从 [Releases](https://github.com/openbkn-ai/bkn-samples/releases) 下载本样例的 `package.tar.gz`，选择**导入离线包**后安装。引用的数据镜像也必须能够在目标集群拉取或提前准备。可安装版本以[官方目录](../../catalog.json)为准，新增源码中的评测资料不会自动替换已有发布包。

## 可以问什么

- 梅西在 WC-2014 和 WC-2022 获得过哪些奖项？
- WC-2022 阿根廷大名单中有哪些球员，他们各上场多少次、进了多少球？
- WC-2022 的射手前五名有哪些并列者？
- 阿根廷 WC-2022 的比赛进球和点球大战记录如何核对？
- WC-1999 的比赛、名单、进球和球员上场明细分别记录了多少行？

## 中文场景评测

已提供 **50 道中文题、参考答案、答案重算与评分脚本**：

| 类别 | 题数 |
| --- | ---: |
| 基础查询统计 | 10 |
| 多表关联 | 12 |
| 排名和跨届对比 | 14 |
| 综合分析 | 14 |

- [评测说明与业务口径](bkn-eval/README.md)
- [问题集](bkn-eval/datasets/question-set-v1.yaml)
- [参考答案](bkn-eval/gold/answer-set-v1.yaml)

由独立外部 Agent 通过 MCP 解答，评测过程中不提供参考答案，完成后按规定字段、排序和业务值核对。评测使用标准对象查询，不调用运行时 SQL、Vega 内部查询接口或平台内部 `bkn-agent`。

从仓库根目录重算参考答案并核对独立输出：

```sh
python3 samples/world-cup/bkn-eval/scripts/recalculate.py --check
python3 samples/world-cup/bkn-eval/scripts/grade_answers.py /absolute/path/answers.json
```

评测集和测试保留在源码仓库，按现有打包规则不进入运行时安装包。执行记录和临时计算文件留在本地。

## 查询口径

比赛按 `matches` 或不同 `match_id` 计数；球队参赛记录是一支球队的一场比赛，每场对应两条记录。球员进球排除乌龙球，球队记账进球包含该队受益的乌龙球；点球大战罚球不加入比赛比分或进球总数。得牌标记可能重叠，按题目分别统计。

当前中文模型的比赛、球队逐场记录各有 10 个展示字段未声明。名称和阶段通过已发布的球队、裁判场次、进球或教练场次对象关联补全。源数据的数值可能返回文本，进行容量比较、行键排序或统计前应转换为数值，并读取完整分页。

## 开发与发布

安装组件及 hooks 以 [sample.yaml](sample.yaml) 为准。安装 hooks 在内部调用 `run.sh`；用户使用一键体验或离线包导入，无需手工执行脚本。其中的历史 SQL 工具注册不是本页体验和评测的调用入口。

修改数据或模型后，按[样例开发指南](../../docs/SAMPLE_DEVELOPMENT_GUIDE.zh-CN.md)构建固定候选、完成实际安装与业务验收，再发布新版本。不要覆盖已经发布的制品。

## 数据来源与许可

数据来自 [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup)，固定提交为 `35a8667f518b07469182ae16d35574dd0e7a00fb`；27 个 CSV 文件的摘要见 [dataset.lock](dataset.lock)。

© 2023 Joshua C. Fjelstul, Ph.D. 数据采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可，分享数据或衍生数据时保留署名和相同方式共享要求。
