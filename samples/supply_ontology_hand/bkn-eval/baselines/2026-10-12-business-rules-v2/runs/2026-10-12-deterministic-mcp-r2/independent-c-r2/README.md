# 独立评判 C · 第二轮

**50 / 50 通过，0 失败。** 全部 M15 / F15 / R9 / S11 纳入评分；不存在缺题、额外题或用其他题填补当前题答案。

只读取授权的最终题/答案集、评分规则与 independent-a-r2 自有冻结答案及 MCP 回执。未读取实现、CSV、root离线结果、历史答案或其他评判者结果。第一轮仍保留于 independent-c，本报告不覆盖第一轮 35/50。

## 身份核验

- 问题 SHA256：`51c60429b17053071ad8eef59de734e3297835430d274b9a58d24082e63e0026`
- 金标 SHA256：`0ed51302d2fe0ddc579d01d16b13aceb391eea594449919bcc8eca52da1596ab`
- A 答案 JSON SHA256：`c1452b7345ce938df79e843f423a34aa782fc4d0d0804e492850292e2b288e06`
- A 答案 Markdown SHA256：`02d041367df503641077a5d2eb3a8e3b9064b52dfe051f254a26ac9cf7999dc7`
- 候选包 SHA256：`b9d87928142a93f01bc1cd45cad1d010a77fa482111dc51d014a110214197d06`
- 安装 ID：`inst-supply-chain-14a1838eceeb4e88b2e4e045d875406c`

上述身份均与 root 先前发送的冻结身份匹配。A manifest 列出文件的 SHA 全部匹配。安装完成时间由 root 通知为 2026-10-12T13:35:48.490981Z；C 不读取安装包或实现，只核验此身份与 A 冻结记录一致。

## 发布 MCP 路径及评分

5 份 A 已读取 Skill 状态均为 published。50 个主 interaction 都是 completed / complete，所有保存 receipt 均 completed。共 14 次 query_metric 和 40 次 execute_tool；13 个函数 ID 匹配已发现 function capability，toolbox_id 匹配 owner_id，均有 function 业务引用；全部指标调用有匹配 metric 业务引用。BKN interaction 参数匹配各题真实 trace。完整逐题调用参数、函数名称及 receipt ID 在 MCP-audit.json。

逐项核对题目参数：默认全仓、F-08/F-09/F-13 的 production_available、无替代/启用替代、共用库存需求数组顺序、完整主料 BOM 查询、物料/数量/需要日均匹配题意。S-08 调用没有显式 business_date 参数，但实际 MCP 输出 business_date=2026-08-25，明确匹配问题；按期供给使用函数确认供应口径。

使用授权 offline_compare 规则，数值容差、布尔类型、字段缺失规则不变。只按 final expected 的必答字段比较，并将 A 等义字段和显式答案文字归一化，不补事实。F-14 node_count 直接来自 A 的 reported_rows_incl_root=77 及完整主料回执；未以 76+1 推断代替。

关键确定性题结果：

| 题目 | 冻结 A 结论 | 核对 |
| --- | --- | --- |
| S-01 | 否；606-000069 缺41、606-000071 缺30、994-000645 缺20 | 通过 |
| S-05 | 共同主料38；382-000005 是且无缺料，P61-000351 否且缺41/30/20 | 通过 |
| S-08 | 库存40、有效按期PO0、按期供给40、缺口200；否 | 通过 |

F-14 完整主料非根行76、含根节点77，无首轮字段矛盾。F-04 的816/51/867、F-08及F-13制造量34、F-15的816/344/1160也都匹配必答金标。

## 交付文件

- judgment.json：全部50题 expected、A 归一化 observed、差异及证据路径。
- summary.json：成绩、冻结SHA、发布路径核验。
- MCP-audit.json：逐题真实调用参数与回执引用。
- portable.json：可携带合并报告，使用仓库相对证据路径与SHA。
- evaluate_round2.py：评分复现脚本，只读取授权来源。
