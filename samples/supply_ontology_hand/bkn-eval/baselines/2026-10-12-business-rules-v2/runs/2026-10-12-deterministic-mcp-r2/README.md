# 确定性业务规则 v3：8081 独立 MCP 全量验收

**50/50，100%。** M15/F15/R9/S11 全部纳入评分。题目和独立 CSV 金标先冻结，A 只读问题、SDK 和发布 MCP 能力；C 对照冻结答案与真实回执独立评分，未读取实现、CSV 或 root 离线结果。未执行数据库 B 对照，不覆盖历史 Benchmark。

## 精确包与数据

- sample 0.1.5 本地开发候选；包 SHA256 `b9d87928142a93f01bc1cd45cad1d010a77fa482111dc51d014a110214197d06`。
- 安装 ID `inst-supply-chain-14a1838eceeb4e88b2e4e045d875406c`；2026-10-12T13:35:48.490981Z 完成，五阶段成功。
- 标准压缩包经正式卸载、离线导入和安装验收。12份 CSV 与主线完全一致，保留三张未来预测单；题目/答案和本报告不进入交付压缩包。
- [源码与数据核对](final-package-source-verification.json)、[安装回执](installation.json)。

## 路径与结果

A 经 MCP 发现并读取五个发布 Skill，执行 14 次指标和 40 次函数调用。50 个交互最终权威状态为 completed/complete，511 个回执均持久化完成。部分 finish 初始快照仍 assembling，已等待 getInteraction 的最终 complete 状态；不以初始快照评分。

- [A 冻结答案](independent-a-r2/answers.md)、[机器答案](independent-a-r2/answers.json)、[完整证据清单](independent-a-r2/manifest.json)。目录内保存全部脱敏原始调用，SHA 可复核。
- [C 独立报告](independent-c-r2/README.md)、[逐题评分](independent-c-r2/judgment.json)、[汇总](independent-c-r2/summary.json)、[调用及回执](mcp-audit.json)。
- [239项测试](pytest.txt)、[离线50题对照](offline-final-comparison.json)、[指标5/5与属性11/11](metric-validation-summary.json)；这些验证独立于 MCP 成绩。

| 题目 | 确定结论 |
| --- | --- |
| S-01 | 库存不能覆盖；606-000069 缺41、606-000071 缺30、994-000645 缺20。 |
| S-05 | 共同主料38；先382-000005×50满足，再P61-000351×60不满足，三个叶子缺口同上。 |
| S-08 | 确认库存40、有效按期PO0、供给40、缺口200，不覆盖240。 |
| F-14 | 完整主料非根行76，含根节点77。 |

## 修订追溯与范围

[首轮35/50](../2026-10-12-deterministic-mcp-r1/README.md)完整保留。首轮揭示 MCP 装载仍用旧主料判断、BOM 两个计数字段口径不一致，以及答案契约包含题目未要求的附加字段。修复只发生在 sample：装载统一主料分类、计数同口径；题目明确主料范围；独立金标投影为必答字段，事实数值没有改动。第二轮重新安装精确包、重新执行全部50题，未复用首轮业务结果。

本成绩针对当前冻结资源池与题目。不将库存能力或确认供应覆盖推断为缺失到货/制造条件下的完整交期承诺；完整制造排程仍有单独验收边界。没有修改平台、发布正式版本或创建新PR。

## 复核

从仓库根目录，用带 PyYAML 的 Python 执行本目录 `independent-c-r2/evaluate_round2.py`，可复核冻结文件SHA、MCP证据与逐题比较。独立CSV重算见上级 `gold-evidence/README.md`。
