# 2026-10-30 external MCP agent

An external agent answered the English 50 questions through MCP on 8081 (bkn-backend EE main 9156ec5) with sample 0.1.2 installed, so it could call the sample's functions. The agent is `mcp_agent.py`: the platform model deepseek-v4-flash (the same model Studio smart Q&A uses) with every tool the BKN MCP server offers. The system prompt names only the knowledge network and asks the agent to check the skills first and follow them. Each question opens a fresh MCP session; the answer set is never given to the agent. Answers and tool calls are in `results.json`.

Result: **50/50 in a single round, no reruns**. The three answers the automatic check missed are correct on manual review: Q-41 and Q-44 describe reasons and lot-location pairs in words rather than codes, and Q-47 says "down 423" instead of "-423". For Q-42 the agent named both the identical duplicate EV-00875 and the conflicting copies of EV-00897; the reference answer now lists both, with no numbers changed. All 15 experience cards also passed the online check after installation.

```bash
BKN_KN=retail_gs1_en_us python mcp_agent.py ../../question-set-v1.yaml <output-dir> --workers 3
```
