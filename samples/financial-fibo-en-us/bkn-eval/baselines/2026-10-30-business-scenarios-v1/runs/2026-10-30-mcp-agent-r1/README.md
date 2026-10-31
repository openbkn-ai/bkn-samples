# 2026-10-30 external MCP agent

An external agent answered the English 50 questions through MCP on 8081 (bkn-backend EE main 9156ec5) with sample 0.2.7 installed, so it could call the sample's functions. The agent is `mcp_agent.py`: the platform model deepseek-v4-flash (the same model Studio smart Q&A uses) with every tool the BKN MCP server offers. The system prompt names only the knowledge network and asks the agent to check the skills first and follow them. Each question opens a fresh MCP session; the answer set is never given to the agent. Answers and tool calls are in `results.json`.

Result: **50/50 in a single round**. Seven questions (Q-04 to Q-10) hit a platform gateway 502 on their first request and only those requests were sent again; no question was rerun because of a wrong answer. The automatic check treats the mathematical minus sign (U+2212) in answers as a hyphen-minus.

Month-end questions read the recorded snapshots with Cypher; look-back questions such as Q-40 to Q-43 (February 15) called `settlement_asof` or `limit_assessment_asof`. All 15 experience cards also passed the online check after installation.

```bash
BKN_KN=financial_fibo_en_us python mcp_agent.py ../../question-set-v1.yaml <output-dir> --workers 3
```
