# 2026-10-30 Studio 智能问答第一轮

8081（bkn-backend EE 主线 9156ec5）安装样例 0.1.17 后，由 Studio 智能问答智能体 `studio_smart_qa` 逐题作答，每题新开会话、只跑一轮，答案集不提供给智能体。逐题回答、工具调用和判分见 `results.json`。

结果：**43/50（86%）**。

| 失败原因 | 题号 |
|---|---|
| 需要 BOM 逐层净扣，但智能体调不到样例函数，只能自行用 Cypher 推算 | Q-26、Q-28、Q-30、Q-34、Q-50 |
| 问法有歧义（已在 PRD、知识网络描述中补充口径，并改写 Q-21 问法，答案不变） | Q-19、Q-21 |

平台的公开问答接口不向模型提供 `execute_tool`、`execute_skill` 和 `run_code`（bkn-foundry `infra/bkn-agent/app/core/public_chat.py`），所以 Studio 智能问答能发现并读取 Skill，却无法调用已发布的函数。外部 Agent 通过 MCP 接入时可以调用。
