# 2026-10-30 external MCP agent

An external agent answered the English 50 questions through MCP on 8081 (bkn-backend EE main 9156ec5) with sample 0.1.5 installed. The agent is `mcp_agent.py`: the platform model deepseek-v4-flash (the same model Studio smart Q&A uses) with every tool the BKN MCP server offers; this sample has no functions, so everything is queried with Cypher. The system prompt names only the knowledge network and asks the agent to check the skills first and follow them. Each question opens a fresh MCP session; the answer set is never given to the agent. Answers, the round each comes from, and tool calls are in `results.json`.

Result: **50/50**. Q-33 lost its connection on the first request (client error, no answer) and was sent again. Q-34 was answered correctly in the first round and was rerun once after the Chinese run led to a Skill change (list each non-compliant execution with its work order, and count after listing); it was correct again. The other 48 questions keep their first-round answers.

Reviewed by hand and correct: Q-27 and Q-28 name operations by sequence number rather than step ID, and Q-29 gives the yield as 95.56%. All 15 experience cards also passed the online check after installation.

```bash
BKN_KN=manufacturing_industry_en_us python mcp_agent.py ../../question-set-v1.yaml <output-dir> --workers 4
```
