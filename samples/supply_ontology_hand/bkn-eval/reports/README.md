# 供应链 BKN-Eval 正式报告

本目录存放供应链 sample 的**正式 A/B/C 测试报告**。历史试跑、调试记录和阶段性对比不属于对外交付，不在本目录保留，也不得作为 Benchmark 结论引用。

## 评测历史

正式 Benchmark 是与平台版本、样例数据快照、题集/答案集版本和智能体运行环境绑定的记录。平台能力、问题集或答案标准升级后，应新增一轮正式报告，不能覆盖既有结论。

| 评测批次 | A：Agent / 模型 | B：Agent / 模型 | C：Agent / 模型 | 数据快照 | 业务日期 | 题集 / 答案集 | 核心结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-31 | POC / DeepSeek Harness / DeepSeek V4 Flash | POC / DeepSeek Harness / DeepSeek V4 Flash | POC / DeepSeek Harness / DeepSeek V4 Flash | 2026-08-13 | 2026-08-25 | question set `v1.1` / answer set `v1.3` | A（BKN）50/50，100%；B（直连数据库）26/50，52%。 |
| 2026-08-30 | OpenClaw `v2026.7.1-2` / DeepSeek V4 Flash | OpenClaw `v2026.7.1-2` / DeepSeek V4 Flash | OpenClaw `v2026.7.1-2` / DeepSeek V4 Flash | 2026-08-13 | 2026-08-25 | question set `v1.1` / answer set `v1.3` | A（BKN）50/50，100%；B（直连数据库）28/50，56%。 |

后续批次请采用独立日期目录（例如 `2026-09-15/`），目录内仍使用本 README 规定的 A/B/C 标准文件名，并在本表追加对应环境与结论。

## 固定输入

- 问题集：[`../datasets/sample-question-set-v1.yaml`](../datasets/sample-question-set-v1.yaml)
- 答案集：[`../datasets/sample-answer-set-v1.yaml`](../datasets/sample-answer-set-v1.yaml)（仅评测者 C 使用）
- 数据快照：`2026-08-13`
- 业务日期：`2026-08-25`

## 正式报告命名

每个正式批次在各自日期目录中使用下列标准文件名：

| 文件 | 内容 |
| --- | --- |
| `path-a-bkn-answer.md` | 路径 A：智能体通过 OpenBKN MCP、供应链知识网络和已发布函数作答的原始报告。 |
| `path-b-direct-db-answer.md` | 路径 B：智能体仅通过同一快照的只读数据库作答的原始报告。 |
| `comparison.md` | 路径 C：依据冻结的 A/B 原始回答与答案集生成的逐题对比报告。 |
| `comparison.html` | 面向业务读者的 HTML 对比报告；结论必须与 `comparison.md` 一致。 |

## 2026-08-31 正式报告

- [A 路径原始答题报告](2026-08-31/path-a-bkn-answer.md)
- [B 路径原始答题报告](2026-08-31/path-b-direct-db-answer.md)
- [逐题对比报告](2026-08-31/comparison.md)
- [面向业务领导的 HTML 对比报告](2026-08-31/comparison.html)

## 2026-08-30 报告截图
| `2026-08-30-benchmark-summary.png` | HTML 报告首页截图：A/B 总体结果与题型准确率。 |
| `2026-08-30-benchmark-analysis.png` | HTML 报告续页截图：关键差异、效率对比与 A 路径表现。 |

- [总体结果与题型准确率](2026-08-30-benchmark-summary.png)
- [关键差异、效率与 A 路径表现](2026-08-30-benchmark-analysis.png)

## 发布边界

报告应使用本仓库内的相对路径。不得记录或暴露个人目录、工作区路径、数据库主机、账号、密码、Token、会话凭据或平台内部地址。

在 A、B 两份原始回答冻结前，答案集不得提供给答题智能体；扩展题默认不计入核心 50 题的结果。报告生成与判定方式见《供应链 BKN-Eval POC 测试评估指南》。
