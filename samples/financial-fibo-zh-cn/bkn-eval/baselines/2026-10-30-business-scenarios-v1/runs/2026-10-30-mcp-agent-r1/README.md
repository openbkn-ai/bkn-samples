# 2026-10-30 外部 MCP 智能体

8081（bkn-backend EE 主线 9156ec5）安装样例 0.2.7 后，由外部智能体通过 MCP 回答中文 50 题，可以调用样例函数。智能体是 `mcp_agent.py`：平台模型 deepseek-v4-flash（与 Studio 智能问答同一模型），加上 BKN MCP 服务提供的全部工具。系统提示只说明知识网络 ID，并要求先查技能、按技能作答。每题新开 MCP 会话，答案集不提供给智能体。逐题回答和工具调用见 `results.json`。

结果：**50/50，一轮**。有 13 题在第一次请求时遇到平台网关 502（Q-03 至 Q-13、Q-15、Q-16，其中 Q-15 两次），只重发了这些请求，没有因答错重跑。自动核对时把回答里的数学减号（U+2212）按普通减号处理。

月末题直接用 Cypher 读已记录快照；Q-40 至 Q-43 等回看 2 月 15 日的题调用了 `settlement_asof` 或 `limit_assessment_asof` 重算。安装后 15 张体验卡也全部通过在线核验。

```bash
BKN_KN=financial_fibo_zh_cn python mcp_agent.py ../../question-set-v1.yaml <输出目录> --workers 3
```
