# 优化评测基线：完整交付 CSV

基线 ID：`supply-current-csv-2026-10-12-v1`。状态：输入已冻结，0.1.5 本地包已完成 8081 卸载重装及数据/能力回归。独立 MCP A/C 验证核心 50/50、100%；时间扩展 4/5，月环比仍失败。见[最新第三包验证记录](runs/2026-10-12-local-015-r3-ac/README.md)，[第二包记录](runs/2026-10-12-local-015-ac/README.md)保留。未执行数据库 B，不是完整 A/B/C 正式 Benchmark。

采用全部 12 个交付 CSV；包括 FUTURE/SHORT/CONTENTION 三张未来预测单。2026-10-12 是仓库 fixture 冻结日期，业务日期仍为 2026-08-25。历史来源与选择原因见 [追溯报告](../../../../../docs/supply-sample-history-forensics.zh-CN.md)。

- [manifest.json](manifest.json)：数据与输入摘要、行数、预期聚合、名称映射和待补运行身份。
- [question-set-v2.yaml](question-set-v2.yaml)：答题 Agent A/B 可读，核心 50 题正文与 v1 一致。
- [answer-set-v2.yaml](answer-set-v2.yaml)：仅评测者 C 可读；更新 M-07=56340、M-08=90、M-12=12/20000，其他 47 题业务答案不变。
- [preflight.sql](preflight.sql)：正式安装数据库的只读前置检查。
- [validate_inputs.py](validate_inputs.py)：不联网、仅用标准库验证输入/数据摘要与预测数据聚合。

运行 `python3 validate_inputs.py`，应显示输入完整性通过。它不是线上 Agent 准确率成绩，不验证指标/函数注册或 loader。

盲测时只向 A/B 提供 `question-set-v2.yaml` 和必要运行权限；manifest、金标、SQL 中的预期值及追溯报告仅供前置核验人员/C 使用，不交给答题 Agent。

正式运行需要记录候选 sample 版本、精确包摘要、数据镜像 digest、部署平台 SHA、Agent/模型版本。输入 manifest 保留冻结输入身份，实际候选运行另存验收记录，不用运行结果改写金标。最新本地测试包为 0.1.5，摘要 `7771413d4ce1071554b8d5521925fb7e6a87350ba74904d7dd31383febc5349f`；该包的全新独立 A/C 已验证最终 50/50，首次无错误 48/50，恢复错误另行披露，运行详情见[实施记录](../../../../../docs/supply-sample-implementation-status.zh-CN.md)。它包含未提交修改，未发布，时间环比门禁尚未通过，不能宣布新版发布验收成功。

`preflight.sql` 的无前缀表名对应当前 MariaDB 样例安装；使用带 `hand_` 前缀的 PostgreSQL 时须明确改表名，并保持完全相同过滤口径。三个 ID 应各命中一行；总行数 137、未关闭 90/56340、U00-000080 12/20000、关闭 47/59582、全量 115922。保留三个 ID 的 string 类型及前导零。

实际部署的数据如果不同，应先修正安装一致性或明确发布另一数据 baseline，不按错误答案或随机线上结果修改金标。数据变化前不得覆盖此 manifest 的数据摘要。

上线后目标是核心 50/50 加 issue 扩展验收全部通过。报告建立独立日期目录，记录 baseline ID 和输入摘要；旧 8 月底 100% 报告保持历史边界。历史对照的精确题集/答案集应从 `2756858` 提取（扩展题不计核心分母），不能仅凭当前 v1 文件的内部版本名恢复。
